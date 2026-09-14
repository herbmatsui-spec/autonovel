"""Unit of Work interface for transaction management."""

from __future__ import annotations
from typing import Protocol, Optional, AsyncGenerator, runtime_checkable
from contextlib import asynccontextmanager

from src.domain.repositories.novel_repository import INovelRepository
from src.domain.repositories.chapter_repository import IChapterRepository
from src.domain.repositories.episode_repository import IEpisodeRepository
from src.domain.repositories.character_repository import ICharacterRepository
from src.domain.repositories.world_bible_repository import IWorldBibleRepository
from src.domain.repositories.plot_repository import IPlotRepository
from src.domain.repositories.branch_repository import IBranchRepository
from src.domain.repositories.audit_repository import IAuditRepository


@runtime_checkable
class IUnitOfWork(Protocol):
    """Unit of Work interface - manages transaction boundaries."""

    # Repository accessors
    @property
    def novels(self) -> INovelRepository:
        """Get novel repository."""
        ...

    @property
    def chapters(self) -> IChapterRepository:
        """Get chapter repository."""
        ...

    @property
    def episodes(self) -> IEpisodeRepository:
        """Get episode repository."""
        ...

    @property
    def characters(self) -> ICharacterRepository:
        """Get character repository."""
        ...

    @property
    def world_bible(self) -> IWorldBibleRepository:
        """Get world bible repository."""
        ...

    @property
    def plots(self) -> IPlotRepository:
        """Get plot repository."""
        ...

    @property
    def branches(self) -> IBranchRepository:
        """Get branch repository."""
        ...

    @property
    def audits(self) -> IAuditRepository:
        """Get audit repository."""
        ...

    # Transaction management
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...

    async def close(self) -> None:
        """Close the unit of work (release resources)."""
        ...

    # Context manager support
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[IUnitOfWork, None]:
        """Context manager for transaction."""
        ...

    # Flush pending changes without committing
    async def flush(self) -> None:
        """Flush pending changes to database."""
        ...