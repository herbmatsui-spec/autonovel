"""Chapter repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.novel import Chapter
from src.domain.value_objects.ids import ChapterId, NovelId


@runtime_checkable
class IChapterRepository(Protocol):
    """Chapter repository interface."""

    async def get_by_id(self, chapter_id: ChapterId) -> Optional[Chapter]:
        """Get chapter by ID."""
        ...

    async def get_by_id_with_episodes(self, chapter_id: ChapterId) -> Optional[Chapter]:
        """Get chapter with all episodes loaded."""
        ...

    async def save(self, chapter: Chapter) -> Chapter:
        """Save chapter (insert or update)."""
        ...

    async def list_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Chapter]:
        """List chapters by novel."""
        ...

    async def list_by_novel_with_episodes(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Chapter]:
        """List chapters with episodes by novel."""
        ...

    async def count_by_novel(self, novel_id: NovelId) -> int:
        """Count chapters in a novel."""
        ...

    async def delete(self, chapter_id: ChapterId) -> bool:
        """Delete chapter by ID. Returns True if deleted."""
        ...

    async def exists(self, chapter_id: ChapterId) -> bool:
        """Check if chapter exists."""
        ...

    async def reorder(self, novel_id: NovelId, chapter_orders: List[tuple[ChapterId, int]]) -> bool:
        """Reorder chapters. chapter_orders is list of (chapter_id, new_order)."""
        ...

    async def get_max_order(self, novel_id: NovelId) -> int:
        """Get maximum order value for chapters in novel."""
        ...

    async def get_by_order(self, novel_id: NovelId, order: int) -> Optional[Chapter]:
        """Get chapter by order in novel."""
        ...