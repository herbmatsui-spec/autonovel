"""World Bible domain entity."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.domain.value_objects.ids import NovelId, SettingId
from src.domain.value_objects.text import TextContent, MarkdownText


@dataclass
class WorldBible:
    """World Bible aggregate root - contains all world settings for a novel."""
    id: SettingId
    novel_id: NovelId
    settings: TextContent
    revealed: TextContent
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # Pending settings (not yet confirmed)
    _pending_settings: dict[str, PendingSetting] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def create(cls, novel_id: NovelId) -> WorldBible:
        """Factory method to create a new world bible."""
        bible_id = SettingId.generate()
        now = datetime.now()
        return cls(
            id=bible_id,
            novel_id=novel_id,
            settings=MarkdownText(""),
            revealed=MarkdownText(""),
            version=1,
            created_at=now,
            last_updated=now,
        )

    def update_settings(self, settings: TextContent, increment_version: bool = True) -> None:
        """Update world settings."""
        self.settings = settings
        self.last_updated = datetime.now()
        if increment_version:
            self.version += 1

    def update_revealed(self, revealed: TextContent) -> None:
        """Update revealed information (known to reader)."""
        self.revealed = revealed
        self.last_updated = datetime.now()

    def add_pending_setting(
        self,
        field_name: str,
        proposed_value: TextContent,
        confidence: float = 0.0,
    ) -> PendingSetting:
        """Add a pending setting for review."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        pending = PendingSetting(
            id=SettingId.generate(),
            novel_id=self.novel_id,
            field_name=field_name,
            proposed_value=proposed_value,
            confidence=confidence,
            status="pending",
            created_at=datetime.now(),
        )
        self._pending_settings[field_name] = pending
        return pending

    def confirm_pending_setting(self, field_name: str) -> Optional[PendingSetting]:
        """Confirm a pending setting and move to main settings."""
        pending = self._pending_settings.pop(field_name, None)
        if pending:
            # Merge into settings (simplified - in reality would merge JSON/YAML)
            self.last_updated = datetime.now()
            self.version += 1
        return pending

    def reject_pending_setting(self, field_name: str) -> Optional[PendingSetting]:
        """Reject a pending setting."""
        return self._pending_settings.pop(field_name, None)

    def get_pending_settings(self) -> list[PendingSetting]:
        """Get all pending settings."""
        return list(self._pending_settings.values())

    def get_pending_setting(self, field_name: str) -> Optional[PendingSetting]:
        """Get a specific pending setting."""
        return self._pending_settings.get(field_name)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "settings": self.settings.content,
            "revealed": self.revealed.content,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorldBible:
        """Deserialize from dictionary."""
        from src.domain.value_objects.ids import SettingId, NovelId
        return cls(
            id=SettingId.from_string(data["id"]),
            novel_id=NovelId.from_string(data["novel_id"]),
            settings=MarkdownText(data["settings"]),
            revealed=MarkdownText(data["revealed"]),
            version=data.get("version", 1),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorldBible):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True, slots=True)
class PendingSetting:
    """Pending setting awaiting confirmation."""
    id: SettingId
    novel_id: NovelId
    field_name: str
    proposed_value: TextContent
    confidence: float
    status: str = "pending"  # pending, confirmed, rejected
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.field_name.strip():
            raise ValueError("Field name cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class Setting:
    """Individual setting entry."""
    id: SettingId
    name: str
    value: TextContent
    category: str
    is_revealed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Setting name cannot be empty")
        if not self.category.strip():
            raise ValueError("Category cannot be empty")

    def mark_revealed(self) -> Setting:
        """Return new setting marked as revealed."""
        return Setting(
            id=self.id,
            name=self.name,
            value=self.value,
            category=self.category,
            is_revealed=True,
            created_at=self.created_at,
            updated_at=datetime.now(),
        )

    def update_value(self, value: TextContent) -> Setting:
        """Return new setting with updated value."""
        return Setting(
            id=self.id,
            name=self.name,
            value=value,
            category=self.category,
            is_revealed=self.is_revealed,
            created_at=self.created_at,
            updated_at=datetime.now(),
        )


@dataclass(frozen=True, slots=True)
class Lore:
    """Lore entry - deeper worldbuilding element."""
    id: SettingId
    novel_id: NovelId
    title: str
    content: TextContent
    category: str  # history, geography, magic_system, technology, culture, etc.
    tags: list[str] = field(default_factory=list)
    is_secret: bool = False  # Hidden from players/readers
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Lore title cannot be empty")
        if not self.category.strip():
            raise ValueError("Category cannot be empty")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        title: str,
        content: TextContent,
        category: str,
        tags: list[str] = None,
        is_secret: bool = False,
    ) -> Lore:
        return cls(
            id=SettingId.generate(),
            novel_id=novel_id,
            title=title,
            content=content,
            category=category,
            tags=tags or [],
            is_secret=is_secret,
        )

    def add_tag(self, tag: str) -> Lore:
        """Return new lore with added tag."""
        new_tags = list(self.tags)
        if tag not in new_tags:
            new_tags.append(tag)
        return Lore(
            id=self.id,
            novel_id=self.novel_id,
            title=self.title,
            content=self.content,
            category=self.category,
            tags=new_tags,
            is_secret=self.is_secret,
            created_at=self.created_at,
            updated_at=datetime.now(),
        )


__all__ = [
    "WorldBible",
    "PendingSetting",
    "Setting",
    "Lore",
]