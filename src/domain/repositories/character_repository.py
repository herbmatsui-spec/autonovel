"""Character repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.character import Character, CharacterArc
from src.domain.value_objects.ids import CharacterId, NovelId


@runtime_checkable
class ICharacterRepository(Protocol):
    """Character repository interface."""

    async def get_by_id(self, character_id: CharacterId) -> Optional[Character]:
        """Get character by ID."""
        ...

    async def save(self, character: Character) -> Character:
        """Save character (insert or update)."""
        ...

    async def list_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Character]:
        """List characters by novel."""
        ...

    async def count_by_novel(self, novel_id: NovelId) -> int:
        """Count characters in a novel."""
        ...

    async def delete(self, character_id: CharacterId) -> bool:
        """Delete character by ID. Returns True if deleted."""
        ...

    async def exists(self, character_id: CharacterId) -> bool:
        """Check if character exists."""
        ...

    async def get_main_characters(self, novel_id: NovelId) -> List[Character]:
        """Get main characters (is_main=True)."""
        ...

    async def get_by_role(
        self,
        novel_id: NovelId,
        role: str,
    ) -> List[Character]:
        """Get characters by role."""
        ...

    async def search_by_name(
        self,
        novel_id: NovelId,
        query: str,
        limit: int = 20,
    ) -> List[Character]:
        """Search characters by name (partial match)."""
        ...

    # CharacterArc methods
    async def save_arc(self, arc: CharacterArc) -> CharacterArc:
        """Save character arc."""
        ...

    async def get_arc_by_id(self, arc_id: CharacterId) -> Optional[CharacterArc]:
        """Get character arc by ID (same as character_id)."""
        ...

    async def list_arcs_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CharacterArc]:
        """List character arcs by novel."""
        ...