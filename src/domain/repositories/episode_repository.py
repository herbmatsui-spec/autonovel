"""Episode repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.novel import Episode
from src.domain.value_objects.ids import EpisodeId, NovelId, ChapterId


@runtime_checkable
class IEpisodeRepository(Protocol):
    """Episode repository interface."""

    async def get_by_id(self, episode_id: EpisodeId) -> Optional[Episode]:
        """Get episode by ID."""
        ...

    async def save(self, episode: Episode) -> Episode:
        """Save episode (insert or update)."""
        ...

    async def list_by_chapter(
        self,
        chapter_id: ChapterId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Episode]:
        """List episodes by chapter."""
        ...

    async def list_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Episode]:
        """List episodes by novel."""
        ...

    async def count_by_chapter(self, chapter_id: ChapterId) -> int:
        """Count episodes in a chapter."""
        ...

    async def count_by_novel(self, novel_id: NovelId) -> int:
        """Count episodes in a novel."""
        ...

    async def delete(self, episode_id: EpisodeId) -> bool:
        """Delete episode by ID. Returns True if deleted."""
        ...

    async def exists(self, episode_id: EpisodeId) -> bool:
        """Check if episode exists."""
        ...

    async def get_latest_by_novel(self, novel_id: NovelId) -> Optional[Episode]:
        """Get latest episode by novel."""
        ...

    async def get_by_chapter_and_episode(
        self,
        chapter_id: ChapterId,
        episode_number: int,
    ) -> Optional[Episode]:
        """Get episode by chapter and episode number."""
        ...

    async def reorder(
        self,
        chapter_id: ChapterId,
        episode_orders: List[tuple[EpisodeId, int]],
    ) -> bool:
        """Reorder episodes in a chapter."""
        ...

    async def get_max_episode_number(self, chapter_id: ChapterId) -> int:
        """Get maximum episode number in a chapter."""
        ...

    async def list_drafts_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Episode]:
        """List draft episodes by novel."""
        ...

    async def list_published_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Episode]:
        """List published episodes by novel."""
        ...