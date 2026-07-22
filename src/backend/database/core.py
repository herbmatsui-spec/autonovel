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
from typing import Any, List, Optional
from urllib.parse import urlparse

import aiosqlite
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import BASE_DIR, DATABASE_URL

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
                except (aiosqlite.Error, sqlite3.Error, OSError, asyncio.TimeoutError) as e:
                    if i == retries - 1:
                        logger.error(f"Final error in {func.__name__} after {retries} retries: {e}\n{traceback.format_exc()}")
                        raise
                    delay = min(base_delay * (1.5 ** i), max_delay)
                    logger.warning(f"Retry {i+1}/{retries} in {func.__name__} after {delay:.1f}s due to: {e}")
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
    def list_backups() -> List[Path]:
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
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class DatabaseConnectionWrapper:
    def __init__(self, sql_conn, dbapi_conn):
        super().__setattr__('sql_conn', sql_conn)
        super().__setattr__('dbapi_conn', dbapi_conn)

    @property
    def cursor(self):
        return self.dbapi_conn.cursor()

    def __getattr__(self, name):
        return getattr(self.dbapi_conn, name)

    def __setattr__(self, name, value):
        if name in ('sql_conn', 'dbapi_conn'):
            super().__setattr__(name, value)
        else:
            setattr(self.dbapi_conn, name, value)

    async def close(self) -> None:
        try:
            await self.dbapi_conn.rollback()
        except Exception:
            pass
        await self.sql_conn.close()

class DatabaseManager:
    def __init__(self, db_url: str, pool_size: int = 10):
        self.db_path = db_url  # 後方互換のため db_path に接続URLを保持
        self._pool_size = pool_size

        is_sqlite = "sqlite" in db_url
        connect_args = {}
        if is_sqlite:
            # タイムアウトを60秒に設定し、待機時間を十分に確保する
            connect_args = {"timeout": 60.0}

        # 接続プールの最適化
        # pool_size: 基本的な保持接続数
        # max_overflow: pool_sizeを超えて一時的に作成可能な接続数
        # pool_recycle: 接続の有効期限（秒）。DB側のタイムアウトより短く設定し、断線を防ぐ
        # pool_pre_ping: 接続を再利用する前に有効性を確認し、切断されていた場合に透過的に再接続する
        self.engine = create_async_engine(
            db_url,
            pool_size=pool_size,
            max_overflow=20,
            pool_recycle=1200,
            pool_pre_ping=True,
            connect_args=connect_args
        )

        # Ensure is_plot_twist column exists in SQLite database
        # (Skipped: Schema updates should be handled by Alembic migrations)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
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
                except Exception:
                    pass

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
            warnings.warn("DatabaseManager.execute() with raw string is deprecated. Please use sqlalchemy.text() or repositories instead.", DeprecationWarning, stacklevel=2)
            sql = text(sql)

        logger.warning(f"DatabaseManager.execute called: {sql}")
        async with self.engine.begin() as conn:
            await conn.execute(sql, params)

    async def fetch_one(self, sql: Any, params: Any = ()) -> Optional[Any]:
        """読み取り専用接続プールを使用した単一行取得"""
        import warnings

        if isinstance(sql, str):
            warnings.warn("DatabaseManager.fetch_one() with raw string is deprecated. Please use sqlalchemy.text() or repositories instead.", DeprecationWarning, stacklevel=2)
            sql = text(sql)

        logger.warning(f"DatabaseManager.fetch_one called: {sql}")
        async with self.engine.connect() as conn:
            result = await conn.execute(sql, params)
            return result.mappings().fetchone()

    async def fetch_all(self, sql: Any, params: Any = ()) -> List[Any]:
        """読み取り専用接続プールを使用した複数行取得"""
        import warnings

        if isinstance(sql, str):
            warnings.warn("DatabaseManager.fetch_all() with raw string is deprecated. Please use sqlalchemy.text() or repositories instead.", DeprecationWarning, stacklevel=2)
            sql = text(sql)

        logger.warning(f"DatabaseManager.fetch_all called: {sql}")
        async with self.engine.connect() as conn:
            result = await conn.execute(sql, params)
            return list(result.mappings().fetchall())

    async def fetch_lastrowid(self, sql: str, params: tuple = ()) -> int:
        async with self.engine.begin() as conn:
            result = await conn.exec_driver_sql(sql, params)
            return result.lastrowid or 0

    async def save_internal_state(self, key: str, value: str, updated_at: str) -> None:
        """データベース非依存な UPSERT 処理で internal_state を保存する"""
        from sqlalchemy import select

        from src.backend.database.models import InternalState
        async with self.get_session() as session:
            async with session.begin():
                stmt = select(InternalState).where(InternalState.key == key)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    existing.value = value
                    existing.updated_at = updated_at
                else:
                    new_state = InternalState(
                        key=key,
                        value=value,
                        updated_at=updated_at
                    )
                    session.add(new_state)



# ==========================================
# グローバルDB取得
# ==========================================
_GLOBAL_DB_MANAGER: Optional[DatabaseManager] = None

def init_db(db_path: str):
    """データベースのマイグレーションを同期的に実行"""
    from alembic.config import Config

    from config import DATABASE_URL

    sync_url = DATABASE_URL
    if "sqlite+aiosqlite" in sync_url:
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
    elif "postgresql+asyncpg" in sync_url:
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

    ini_path = BASE_DIR / "alembic.ini"
    print(f"DEBUG: ini_path={ini_path}, exists={ini_path.exists()}")
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    # テスト環境などの一時的なDBでは、マイグレーションではなくBase.metadata.create_allで
    # 最新のスキーマを強制的に作成することで、不整合を防ぐ
    from sqlalchemy import create_engine

    from src.backend.database.models import Base

    # sync_url を使用して同期的なエンジンを作成し、テーブルを作成
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)

    # 本来のマイグレーションも実行したい場合は以下を有効にするが、
    # create_all の後は不整合が起きる可能性があるため、ここでは create_all を優先する
    # command.upgrade(alembic_cfg, "head")

def get_db_manager() -> DatabaseManager:
    """
    DBマネージャーを取得。
    """
    global _GLOBAL_DB_MANAGER
    if _GLOBAL_DB_MANAGER is not None:
        return _GLOBAL_DB_MANAGER

    from config import DATABASE_URL
    manager = DatabaseManager(DATABASE_URL)
    _GLOBAL_DB_MANAGER = manager
    return manager


_sync_engine = None
_sync_session_factory = None


def get_sync_db_manager():
    """同期的なDB操作用のエンジンとセッションファクトリを取得する"""
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        from config import DATABASE_URL
        sync_url = DATABASE_URL
        if "sqlite+aiosqlite" in sync_url:
            sync_url = sync_url.replace("sqlite+aiosqlite:///", "sqlite:///")
        elif "postgresql+asyncpg" in sync_url:
            sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")
        _sync_engine = create_engine(sync_url)
        _sync_session_factory = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_session_factory


def set_db_manager(manager: Optional[DatabaseManager]) -> None:
    """グローバルDBマネージャーを明示的にセット（主にテスト用DIで使用）"""
    global _GLOBAL_DB_MANAGER
    _GLOBAL_DB_MANAGER = manager




