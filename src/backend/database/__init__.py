from __future__ import annotations

"""
database/__init__.py - データベースパッケージのパブリックインターフェース（後方互換性保証用Facade）
"""
# 既存ファイルが database からモデルを間接インポートしているため、モデルも再エクスポートする
from src.models import (
    BibleDbModel,
    BookDbModel,
    BranchDbModel,
    ChapterDbModel,
    CharacterDbModel,
    PlotDbModel,
    PromptVersionDbModel,
    WorldBible,
)

from .core import (
    DatabaseManager,
    WorkspaceManager,
    get_db_manager,
    init_db,
    retry_with_logging,
    set_db_manager,
)
from .repository import DataRepository
from .uow import UnitOfWork


def get_db():
    """FastAPI Depends 用の DB セッションプロバイダ。"""
    mgr = get_db_manager()
    session = mgr.get_session()
    try:
        yield session
    finally:
        session.close()


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
