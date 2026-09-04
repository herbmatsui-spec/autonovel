from __future__ import annotations

"""
database/core.py - データベース接続および低レベルインフラ管理
"""
import asyncio
import functools
import logging
import shutil
import sqlite3
import time
import traceback
from pathlib import Path
from typing import Any

import aiosqlite
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

try:
    from src.backend.config import ROOT_DIR as BASE_DIR
    from src.backend.config import settings

    DATABASE_URL = settings.DATABASE_URL
except ImportError:
    try:
        from config import BASE_DIR, DATABASE_URL
    except ImportError:
        from pathlib import Path

        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        DATABASE_URL = f"sqlite:///{BASE_DIR / 'storage' / 'autonovel.db'}"

logger = logging.getLogger(__name__)


# ==========================================
# リトライデコレータ
# ==========================================
def retry_with_logging(retries: int = 15, base_delay: float = 0.1, max_delay: float = 60.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except (TimeoutError, aiosqlite.Error, sqlite3.Error, OSError) as e:
                    if i == retries - 1:
                        logger.error(
                            f"Final error in {func.__name__} after {retries} retries: {e}\n{traceback.format_exc()}"
                        )
                        raise
                    delay = min(base_delay * (1.5**i), max_delay)
                    logger.warning(
                        f"Retry {i + 1}/{retries} in {func.__name__} after {delay:.1f}s due to: {e}"
                    )
                    await asyncio.sleep(delay)

        return wrapper

    return decorator


# ==========================================
# WorkspaceManager（ファイルパス管理）
# ==========================================
class WorkspaceManager:
    """ディレクトリ構造とファイルパスを安全に管理する"""

    @staticmethod
    def get_path(filename: str) -> str:
        return str(BASE_DIR / filename)

    @staticmethod
    def list_backups() -> list[Path]:
        return sorted(BASE_DIR.glob("*.bak_*.db"), key=lambda x: x.stat().st_mtime, reverse=True)

    @staticmethod
    def create_snapshot(db_path: str) -> str:
        """DBのスナップショット（バックアップ）を作成"""
        src = Path(db_path)
        if src.exists():
            dst = src.with_suffix(f".bak_{int(time.time())}.db")
            shutil.copy2(src, dst)
            logger.info(f"Snapshot created: {dst.name}")
            return str(dst)
        return ""


# ==========================================
# DatabaseManager（低レベルSQLite/PostgreSQL操作 - SQLAlchemy コネクションプール版）
# ==========================================
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class DatabaseConnectionWrapper:
    def __init__(self, sql_conn, dbapi_conn):
        super().__setattr__("sql_conn", sql_conn)
        super().__setattr__("dbapi_conn", dbapi_conn)

    @property
    def cursor(self):
        return self.dbapi_conn.cursor()

    def commit(self):
        return self.dbapi_conn.commit()

    def rollback(self):
        return self.dbapi_conn.rollback()

    def execute(self, sql, params=()):
        return self.dbapi_conn.execute(sql, params)

    def __setattr__(self, name, value):
        if name in ("sql_conn", "dbapi_conn"):
            super().__setattr__(name, value)
        else:
            setattr(self.dbapi_conn, name, value)

    def fetchone(self):
        """単一行を取得"""
        return self.dbapi_conn.fetchone()

    def fetchall(self):
        """全行を取得"""
        return self.dbapi_conn.fetchall()

    async def close(self) -> None:
        try:
            await self.dbapi_conn.rollback()
        except Exception as exc:
            # close 時の rollback 失敗はクリティカルではないが、追跡用にログを出力する
            logger.debug("DatabaseConnectionWrapper.close: rollback 失敗: %s", exc)
        await self.sql_conn.close()


class DatabaseManager:
    def __init__(self, db_url: str, pool_size: int = 10):
        self.db_path = db_url  # 後方互換のため db_path に接続URLを保持
        self._pool_size = pool_size
        self._warned_about_str_sql = False  # DeprecationWarning の重複抑制

        is_sqlite = "sqlite" in db_url
        connect_args = {}
        if is_sqlite:
            # タイムアウトを60秒に設定し、待機時間を十分に確保する
            connect_args = {"timeout": 60.0}

        engine_kwargs: dict[str, Any] = {
            "connect_args": connect_args,
            "pool_pre_ping": True,
        }
        if not is_sqlite:
            engine_kwargs.update(
                {
                    "pool_size": pool_size,
                    "max_overflow": 20,
                    "pool_recycle": 1200,
                }
            )

        if db_url.startswith("sqlite:///"):
            async_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif db_url.startswith("sqlite:"):
            async_url = db_url.replace("sqlite:", "sqlite+aiosqlite:")
        elif db_url.startswith("postgresql://"):
            async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            async_url = db_url

        self.engine = create_async_engine(
            async_url,
            **engine_kwargs,
        )

        # Ensure is_plot_twist column exists in SQLite database
        # (Skipped: Schema updates should be handled by Alembic migrations)

        self.session_factory = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

        if is_sqlite:

            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                # WALモードを強制的に有効化し、並行性を向上させる
                cursor.execute("PRAGMA journal_mode=WAL;")
                # 書き込み待機時間を30秒に設定（database is locked 防止）
                cursor.execute("PRAGMA busy_timeout = 30000;")
                # 書き込み性能を向上させ、ディスクI/Oを最適化
                cursor.execute("PRAGMA synchronous=NORMAL;")
                # 外部キー制約を有効化
                cursor.execute("PRAGMA foreign_keys=ON;")
                # チェックポイント間隔を調整
                cursor.execute("PRAGMA wal_autocheckpoint=1000;")
                # キャッシュサイズを拡張（約64MB）
                cursor.execute("PRAGMA cache_size=-64000;")
                # メモリマップサイズを拡張（256MB）
                cursor.execute("PRAGMA mmap_size=268435456;")
                cursor.close()

            @event.listens_for(self.engine.sync_engine, "checkin")
            def reset_on_checkin(dbapi_connection, connection_record):
                try:
                    dbapi_connection.rollback()
                except Exception as exc:
                    # checkin 時の rollback 失敗は次回の接続で再試行されるためデバッグログのみ
                    logger.debug("reset_on_checkin rollback 失敗: %s", exc)

    def get_session(self) -> AsyncSession:
        """SQLAlchemyのAsyncSessionを取得する"""
        return self.session_factory()

    @retry_with_logging(retries=5, base_delay=0.5)
    async def get_conn(self) -> DatabaseConnectionWrapper:
        """SQLAlchemyのコネクションプールから接続を取得し、aiosqlite互換ラッパーを返す"""
        sql_conn = await self.engine.connect()
        raw_conn = await sql_conn.get_raw_connection()
        dbapi_conn = raw_conn._connection
        return DatabaseConnectionWrapper(sql_conn, dbapi_conn)

    async def get_read_conn(self) -> DatabaseConnectionWrapper:
        """読み取り専用接続（プールから再利用）"""
        return await self.get_conn()

    async def release_read_conn(self, conn: DatabaseConnectionWrapper) -> None:
        """読み取り専用接続をプールに返却"""
        await conn.close()

    async def enqueue_write(self, sql: str, params: tuple = ()) -> None:
        """後方互換用: 直接書き込みを実行"""
        await self.execute(sql, params)

    async def flush_writes(self) -> None:
        """後方互換用: ダミー"""
        pass

    async def execute(self, sql: Any, params: Any = ()) -> None:
        import warnings

        if isinstance(sql, str):
            if not self._warned_about_str_sql:
                warnings.warn(
                    "DatabaseManager.execute() with raw string is deprecated. Please use sqlalchemy.text() or repositories instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                self._warned_about_str_sql = True
            sql = text(sql)

        logger.debug("DatabaseManager.execute called: %s", sql)
        async with self.engine.begin() as conn:
            await conn.execute(sql, params)

    async def fetch_one(self, sql: Any, params: Any = ()) -> Any | None:
        """読み取り専用接続プールを使用した単一行取得"""
        import warnings

        if isinstance(sql, str):
            if not self._warned_about_str_sql:
                warnings.warn(
                    "DatabaseManager.fetch_one() with raw string is deprecated. Please use sqlalchemy.text() or repositories instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                self._warned_about_str_sql = True
            sql = text(sql)

        logger.debug("DatabaseManager.fetch_one called: %s", sql)
        async with self.engine.connect() as conn:
            result = await conn.execute(sql, params)
            return result.mappings().fetchone()

    async def fetch_all(self, sql: Any, params: Any = ()) -> list[Any]:
        """読み取り専用接続プールを使用した複数行取得"""
        import warnings

        if isinstance(sql, str):
            if not self._warned_about_str_sql:
                warnings.warn(
                    "DatabaseManager.fetch_all() with raw string is deprecated. Please use sqlalchemy.text() or repositories instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                self._warned_about_str_sql = True
            sql = text(sql)

        logger.debug("DatabaseManager.fetch_all called: %s", sql)
        async with self.engine.connect() as conn:
            result = await conn.execute(sql, params)
            return list(result.mappings().fetchall())

    async def fetch_lastrowid(self, sql: str, params: tuple = ()) -> int:
        async with self.engine.begin() as conn:
            result = await conn.exec_driver_sql(sql, params)
            return result.lastrowid or 0

    async def save_internal_state(self, key: str, value: str, updated_at: Any = None) -> None:
        """データベース非依存な UPSERT 処理で internal_state を保存する"""
        from datetime import datetime

        from sqlalchemy import select

        from src.backend.database.models import InternalState

        dt_val: datetime
        if isinstance(updated_at, datetime):
            dt_val = updated_at
        elif isinstance(updated_at, str):
            try:
                dt_val = datetime.fromisoformat(updated_at)
            except ValueError:
                dt_val = datetime.now()
        else:
            dt_val = datetime.now()

        async with self.get_session() as session:
            async with session.begin():
                stmt = select(InternalState).where(InternalState.key == key)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    existing.value = value
                    existing.updated_at = dt_val
                else:
                    new_state = InternalState(key=key, value=value, updated_at=dt_val)
                    session.add(new_state)


# ==========================================
# グローバルDB取得
# ==========================================


def init_db(db_path: str = ""):
    """データベースのマイグレーションまたはテーブル作成を同期的に実行"""
    import os

    sync_url = os.environ.get("DATABASE_URL") or DATABASE_URL
    logger.debug("[init_db] sync_url=%s", sync_url)
    if "sqlite+aiosqlite" in sync_url:
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
    elif "postgresql+asyncpg" in sync_url:
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

    import src.backend.database.models  # noqa
    import src.infrastructure.database.models  # noqa
    from src.backend.database.models import Base as BackendBase
    from src.infrastructure.database.models import Base as InfraBase

    engine_obj = create_engine(sync_url)
    InfraBase.metadata.create_all(engine_obj)
    BackendBase.metadata.create_all(engine_obj)


def get_db_manager() -> DatabaseManager:
    logger.debug("[core] get_db_manager called - returning patched manager")
    return DatabaseManager(DATABASE_URL)


_sync_engine = None
_sync_session_factory = None


def _get_sync_engine_and_factory():
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        sync_url = DATABASE_URL
        if "sqlite+aiosqlite" in sync_url:
            sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
        elif "postgresql+asyncpg" in sync_url:
            sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")
        _sync_engine = create_engine(sync_url)
        _sync_session_factory = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_engine, _sync_session_factory


class _SessionLocalProxy:
    def __call__(self, *args, **kwargs):
        _, factory = _get_sync_engine_and_factory()
        return factory(*args, **kwargs)


class _EngineProxy:
    def __getattr__(self, name):
        eng, _ = _get_sync_engine_and_factory()
        return getattr(eng, name)


SessionLocal = _SessionLocalProxy()
engine = _EngineProxy()


def set_db_manager(manager: DatabaseManager | None) -> None:
    """グローバルDBマネージャーを明示的にセット（主にテスト用DIで使用）"""
    logger.warning("set_db_manager is deprecated. Use DI container instead.")
    try:
        from src.core.container import AppContainer

        AppContainer.db.override(manager)
    except Exception as exc:
        logger.warning("AppContainer.db.override に失敗: %s", exc, exc_info=True)
