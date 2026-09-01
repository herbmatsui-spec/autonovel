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
    """FastAPI Depends 用の DB セッションプロバイダ。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


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
    "get_db_manager",
    "init_db",
    "retry_with_logging",
    "set_db_manager",
    # Repository & UoW
    "DataRepository",
    "UnitOfWork",
]
