"""Novel repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.novel import Novel
from src.domain.value_objects.ids import NovelId
from src.domain.value_objects.metadata import NovelStatus, NovelMode


@runtime_checkable
class INovelRepository(Protocol):
    """Novel repository interface - defines contract for novel persistence."""

    async def get_by_id(self, novel_id: NovelId) -> Optional[Novel]:
        """Get novel by ID."""
        ...

    async def get_by_id_with_relations(self, novel_id: NovelId) -> Optional[Novel]:
        """Get novel with all relations loaded."""
        ...

    async def save(self, novel: Novel) -> Novel:
        """Save novel (insert or update)."""
        ...

    async def list_all(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[NovelStatus] = None,
        mode: Optional[NovelMode] = None,
        author_id: Optional[str] = None,
    ) -> List[Novel]:
        """List novels with optional filters."""
        ...

    async def list_by_author(
        self,
        author_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Novel]:
        """List novels by author."""
        ...

    async def count(
        self,
        status: Optional[NovelStatus] = None,
        mode: Optional[NovelMode] = None,
        author_id: Optional[str] = None,
    ) -> int:
        """Count novels with optional filters."""
        ...

    async def delete(self, novel_id: NovelId) -> bool:
        """Delete novel by ID. Returns True if deleted."""
        ...

    async def exists(self, novel_id: NovelId) -> bool:
        """Check if novel exists."""
        ...

    async def update_status(self, novel_id: NovelId, status: NovelStatus) -> bool:
        """Update novel status. Returns True if updated."""
        ...

    async def update_mode(self, novel_id: NovelId, mode: NovelMode) -> bool:
        """Update novel mode. Returns True if updated."""
        ...

    async def add_cost(self, novel_id: NovelId, cost: float, tokens: int) -> bool:
        """Add cost to novel. Returns True if updated."""
        ...

    async def get_latest_updated(
        self,
        limit: int = 10,
        author_id: Optional[str] = None,
    ) -> List[Novel]:
        """Get latest updated novels."""
        ...

    async def search_by_title(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Novel]:
        """Search novels by title (partial match)."""
        ...