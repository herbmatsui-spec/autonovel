from __future__ import annotations
"""
database/core.py - データベース接続および低レベルインフラ管理
"""
import asyncio
import functools
import logging
import os
import shutil
import sqlite3
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite
from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

try:
    from src.backend.config import ROOT_DIR as BASE_DIR
    from src.backend.config import settings

    DATABASE_URL = settings.DATABASE_URL
except ImportError:
            try:
                from config import BASE_DIR, DATABASE_URL
            except ImportError:
                BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
                DATABASE_URL = f"sqlite:///{BASE_DIR / 'storage' / 'autonovel.db'}"

logger = logging.getLogger(__name__)


class DatabaseConnectionWrapper:
    """Compatibility shim for legacy database connection wrapper."""
    pass


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


class DatabaseManager:
    def __init__(self, db_url: str, pool_size: int = 10):
        self.db_path = db_url  # 後方互換のため db_path に接続URLを保持
        self._pool_size = pool_size

        is_sqlite = "sqlite" in db_url
        connect_args = {}
        if is_sqlite:
            # タイムアウトを60秒に設定し、待機時間を十分に確保する
            connect_args = {"timeout": 60.0}

        engine_kwargs: dict[str, Any] = {
            "connect_args": connect_args,
            "pool_pre_ping": True,
        }
        if os.getenv("USE_NULL_POOL", "0") in ("1", "true", "True"):
            engine_kwargs["poolclass"] = NullPool
        elif not is_sqlite:
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
        elif db_url.startswith("postgresql+psycopg2://"):
            async_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        elif db_url.startswith("postgresql+psycopg://"):
            async_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        else:
            async_url = db_url

        self.engine = create_async_engine(
            async_url,
            **engine_kwargs,
        )

        # Configure SQLite engine if applicable - centralized in one place
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

        self.session_factory = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    def get_session(self) -> AsyncSession:
        """SQLAlchemyのAsyncSessionを取得する"""
        return self.session_factory()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncConnection]:
        """SQLAlchemy標準のAsyncConnectionをコンテキストマネージャで返却"""
        async with self.engine.connect() as conn:
            yield conn

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[AsyncConnection]:
        """トランザクション付きのAsyncConnectionをコンテキストマネージャで返却"""
        async with self.engine.begin() as conn:
            yield conn

    # 後方互換用: 非推奨のget_conn
    @retry_with_logging(retries=5, base_delay=0.5)
    async def get_conn(self):
        """非推奨: SQLAlchemyのコネクションプールから接続を取得し、aiosqlite互換ラッパーを返す
        
        代わりに `connection()` または `begin()` コンテキストマネージャを使用してください。
        """
        import warnings
        warnings.warn(
            "DatabaseManager.get_conn() is deprecated. Use connection() or begin() context managers instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        sql_conn = await self.engine.connect()
        raw_conn = await sql_conn.get_raw_connection()
        dbapi_conn = raw_conn._connection
        
        # 簡易ラッパー（最小限の互換性のみ）
        class _CompatWrapper:
            def __init__(self, dbapi_conn, sql_conn):
                self.dbapi_conn = dbapi_conn
                self.sql_conn = sql_conn
            
            @property
            def cursor(self):
                return self.dbapi_conn.cursor()
            
            def commit(self):
                return self.dbapi_conn.commit()
            
            def rollback(self):
                return self.dbapi_conn.rollback()
            
            def execute(self, sql, params=()):
                return self.dbapi_conn.execute(sql, params)
            
            def fetchone(self):
                return self.dbapi_conn.fetchone()
            
            def fetchall(self):
                return self.dbapi_conn.fetchall()
            
            async def close(self):
                try:
                    await self.dbapi_conn.rollback()
                except Exception:
                    pass
                await self.sql_conn.close()
        
        return _CompatWrapper(dbapi_conn, sql_conn)

    async def get_read_conn(self):
        """非推奨: 読み取り専用接続（プールから再利用）"""
        import warnings
        warnings.warn(
            "DatabaseManager.get_read_conn() is deprecated. Use connection() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.get_conn()

    async def release_read_conn(self, conn) -> None:
        """非推奨: 読み取り専用接続をプールに返却"""
        import warnings
        warnings.warn(
            "DatabaseManager.release_read_conn() is deprecated. Use connection() context manager instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if hasattr(conn, 'close'):
            await conn.close()

    async def enqueue_write(self, sql: str, params: tuple = ()) -> None:
        """後方互換用: 直接書き込みを実行"""
        await self.execute(sql, params)

    async def flush_writes(self) -> None:
        """後方互換用: ダミー"""
        pass

    async def execute(self, sql: Any, params: Any = ()) -> None:
        """SQLを実行する。sqlalchemy.text() でラップされたクエリのみ受け付ける。"""
        if isinstance(sql, str):
            raise TypeError(
                "DatabaseManager.execute() no longer accepts raw strings. "
                "Please use sqlalchemy.text() for SQL queries."
            )

        logger.debug("DatabaseManager.execute called: %s", sql)
        async with self.engine.begin() as conn:
            await conn.execute(sql, params)

    async def fetch_one(self, sql: Any, params: Any = ()) -> Any | None:
        """単一行を取得する。sqlalchemy.text() でラップされたクエリのみ受け付ける。"""
        if isinstance(sql, str):
            raise TypeError(
                "DatabaseManager.fetch_one() no longer accepts raw strings. "
                "Please use sqlalchemy.text() for SQL queries."
            )

        logger.debug("DatabaseManager.fetch_one called: %s", sql)
        async with self.engine.connect() as conn:
            result = await conn.execute(sql, params)
            return result.mappings().fetchone()

    async def fetch_all(self, sql: Any, params: Any = ()) -> list[Any]:
        """複数行を取得する。sqlalchemy.text() でラップされたクエリのみ受け付ける。"""
        if isinstance(sql, str):
            raise TypeError(
                "DatabaseManager.fetch_all() no longer accepts raw strings. "
                "Please use sqlalchemy.text() for SQL queries."
            )

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
    from src.infrastructure.database.models import Base as InfraBase

    engine_obj = create_engine(sync_url)
    # BackendBase と InfraBase は同一の基底メタデータを共有しているため 1 回で同期
    InfraBase.metadata.create_all(engine_obj)

    # 初回起動時に作品が存在しない場合は初期作品を自動シード
    try:
        from sqlalchemy.orm import Session
        from src.backend.database.models import Book
        with Session(engine_obj) as session:
            existing_count = session.query(Book).count()
            if existing_count == 0:
                default_book = Book(
                    id=1,
                    title="はじめての物語",
                    genre="ハイファンタジー (R15)",
                    concept="古代魔導剣術を受け継いだ少年の冒険譚",
                    synopsis="薄暗いダンジョンの中、15歳の青年アルトは古代の剣を手に取った。",
                    catchcopy="運命の剣が、少年の世界を変える。",
                    target_eps=10,
                    mode="studio",
                    status="draft",
                )
                session.add(default_book)
                session.commit()
                logger.info("[init_db] Seeded initial default book (id=1)")
    except Exception as e:
        logger.warning("[init_db] Failed to seed default book: %s", e)


_async_db_manager: DatabaseManager | None = None
_cached_async_url: str | None = None


def get_db_manager() -> DatabaseManager:
    global _async_db_manager, _cached_async_url
    if _async_db_manager is None or _cached_async_url != DATABASE_URL:
        logger.debug("[core] Initializing singleton DatabaseManager with url=%s", DATABASE_URL)
        _async_db_manager = DatabaseManager(DATABASE_URL)
        _cached_async_url = DATABASE_URL
    return _async_db_manager


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

        if manager is None:
            # None の場合は override を解除して元のプロバイダに戻す（コンテナ汚染防止）
            AppContainer.db.reset_override()
        else:
            AppContainer.db.override(manager)
    except Exception as exc:
        logger.warning("AppContainer.db.override に失敗: %s", exc, exc_info=True)
