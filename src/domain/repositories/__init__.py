"""Repository interfaces package."""

from src.domain.repositories.novel_repository import INovelRepository
from src.domain.repositories.chapter_repository import IChapterRepository
from src.domain.repositories.episode_repository import IEpisodeRepository
from src.domain.repositories.character_repository import ICharacterRepository
from src.domain.repositories.world_bible_repository import IWorldBibleRepository
from src.domain.repositories.plot_repository import IPlotRepository
from src.domain.repositories.branch_repository import IBranchRepository
from src.domain.repositories.audit_repository import IAuditRepository
from src.domain.repositories.unit_of_work import IUnitOfWork

__all__ = [
    "INovelRepository",
    "IChapterRepository",
    "IEpisodeRepository",
    "ICharacterRepository",
    "IWorldBibleRepository",
    "IPlotRepository",
    "IBranchRepository",
    "IAuditRepository",
    "IUnitOfWork",
]