"""World Bible repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.world_bible import WorldBible, Setting, Lore
from src.domain.value_objects.ids import NovelId, SettingId, LoreId
from src.domain.value_objects.metadata import SettingType


@runtime_checkable
class IWorldBibleRepository(Protocol):
    """World Bible repository interface."""

    async def get_by_novel(self, novel_id: NovelId) -> Optional[WorldBible]:
        """Get world bible by novel ID."""
        ...

    async def save(self, bible: WorldBible) -> WorldBible:
        """Save world bible (insert or update)."""
        ...

    async def delete(self, novel_id: NovelId) -> bool:
        """Delete world bible by novel ID. Returns True if deleted."""
        ...

    async def exists(self, novel_id: NovelId) -> bool:
        """Check if world bible exists for novel."""
        ...

    # Settings
    async def get_setting(self, setting_id: SettingId) -> Optional[Setting]:
        """Get setting by ID."""
        ...

    async def save_setting(self, setting: Setting) -> Setting:
        """Save setting (insert or update)."""
        ...

    async def list_settings_by_novel(
        self,
        novel_id: NovelId,
        setting_type: Optional[SettingType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Setting]:
        """List settings by novel, optionally filtered by type."""
        ...

    async def count_settings_by_novel(
        self,
        novel_id: NovelId,
        setting_type: Optional[SettingType] = None,
    ) -> int:
        """Count settings in a novel."""
        ...

    async def delete_setting(self, setting_id: SettingId) -> bool:
        """Delete setting by ID. Returns True if deleted."""
        ...

    async def get_settings_by_type(
        self,
        novel_id: NovelId,
        setting_type: SettingType,
    ) -> List[Setting]:
        """Get all settings of a specific type."""
        ...

    # Lore
    async def get_lore(self, lore_id: LoreId) -> Optional[Lore]:
        """Get lore by ID."""
        ...

    async def save_lore(self, lore: Lore) -> Lore:
        """Save lore (insert or update)."""
        ...

    async def list_lore_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Lore]:
        """List lore by novel."""
        ...

    async def count_lore_by_novel(self, novel_id: NovelId) -> int:
        """Count lore entries in a novel."""
        ...

    async def delete_lore(self, lore_id: LoreId) -> bool:
        """Delete lore by ID. Returns True if deleted."""
        ...

    async def search_lore_by_tags(
        self,
        novel_id: NovelId,
        tags: List[str],
        limit: int = 20,
    ) -> List[Lore]:
        """Search lore by tags."""
        ...

    async def get_pending_settings(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Setting]:
        """Get pending (unconfirmed) settings."""
        ...

    async def confirm_setting(self, setting_id: SettingId) -> bool:
        """Mark setting as confirmed. Returns True if updated."""
        ...