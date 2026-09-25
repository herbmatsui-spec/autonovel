from __future__ import annotations

"""
database/__init__.py - データベースパッケージのパブリックインターフェース（後方互換性保証用Facade）
"""
# 既存ファイルが database からモデルを間接インポートしているため、モデルも再エクスポートする
from .core import (
    DatabaseManager,
    SessionLocal,
    WorkspaceManager,
    engine,
    get_db_manager,
    init_db,
    retry_with_logging,
    set_db_manager,
)
from .models import (
    BibleDbModel,
    BookDbModel,
    BranchDbModel,
    ChapterDbModel,
    CharacterDbModel,
    PlotDbModel,
    PromptVersionDbModel,
    WorldBible,
)
from .repository import DataRepository
from .uow import UnitOfWork


def get_db():
    """FastAPI Depends 用の同期 DB セッションプロバイダ (同期ルーター用)。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


async def get_async_db():
    """FastAPI Depends 用の非同期 DB セッションプロバイダ (非同期ルーター用)。"""
    mgr = get_db_manager()
    session = mgr.get_session()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_uow():
    """FastAPI Depends 用の UnitOfWork プロバイダ。"""
    mgr = get_db_manager()
    async with UnitOfWork(mgr) as uow:
        yield uow


__all__ = [
    # Models
    "BibleDbModel",
    "BookDbModel",
    "BranchDbModel",
    "ChapterDbModel",
    "CharacterDbModel",
    "PlotDbModel",
    "PromptVersionDbModel",
    "WorldBible",
    # Core
    "DatabaseManager",
    "WorkspaceManager",
    "engine",
    "get_db_manager",
    "init_db",
    "retry_with_logging",
    "set_db_manager",
    # Session providers
    "get_db",
    "get_async_db",
    "get_uow",
]
