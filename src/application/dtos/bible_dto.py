"""World Bible DTOs."""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class GenerateBibleDTO(BaseModel):
    """DTO for generating a world bible."""

    novel_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    concept: str = Field(default="")
    genre: str = Field(default="")
    existing_settings: Optional[list[dict]] = None
    existing_lore: Optional[list[dict]] = None
    detail_level: str = Field(default="normal")

    model_config = MODEL_CONFIG_DEFAULTS


class CreateSettingDTO(BaseModel):
    """DTO for creating a setting."""

    bible_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1)  # "geography", "culture", "magic_system", "technology", "organization", "history"
    description: str = Field(default="")
    details: dict = Field(default_factory=dict)
    related_entities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS


class UpdateSettingDTO(BaseModel):
    """DTO for updating a setting."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = None
    description: Optional[str] = None
    details: Optional[dict] = None
    related_entities: Optional[list[str]] = None
    tags: Optional[list[str]] = None

    model_config = MODEL_CONFIG_DEFAULTS


class CreateLoreDTO(BaseModel):
    """DTO for creating a lore entry."""

    bible_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1)  # "myth", "legend", "history", "prophecy", "rule", "custom"
    content: str = Field(default="")
    source: str = Field(default="")
    reliability: int = Field(default=100, ge=0, le=100)
    related_settings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS


class UpdateLoreDTO(BaseModel):
    """DTO for updating a lore entry."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    reliability: Optional[int] = Field(default=None, ge=0, le=100)
    related_settings: Optional[list[str]] = None
    tags: Optional[list[str]] = None

    model_config = MODEL_CONFIG_DEFAULTS


class SettingDTO(BaseModel):
    """DTO for setting response."""

    id: str
    bible_id: str
    name: str
    category: str
    description: str
    details: dict
    related_entities: list[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, setting: "Setting") -> "SettingDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(setting.id),
            bible_id=str(setting.bible_id),
            name=setting.name,
            category=setting.category,
            description=setting.description,
            details=setting.details,
            related_entities=setting.related_entities,
            tags=setting.tags,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )


class LoreDTO(BaseModel):
    """DTO for lore response."""

    id: str
    bible_id: str
    title: str
    category: str
    content: str
    source: str
    reliability: int
    related_settings: list[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, lore: "Lore") -> "LoreDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(lore.id),
            bible_id=str(lore.bible_id),
            title=lore.title,
            category=lore.category,
            content=lore.content,
            source=lore.source,
            reliability=lore.reliability,
            related_settings=lore.related_settings,
            tags=lore.tags,
            created_at=lore.created_at,
            updated_at=lore.updated_at,
        )


class BibleResponseDTO(BaseModel):
    """DTO for world bible response."""

    id: str
    novel_id: str
    branch_id: str
    settings: list[SettingDTO] = Field(default_factory=list)
    lore: list[LoreDTO] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, bible: "WorldBible") -> "BibleResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(bible.id),
            novel_id=str(bible.novel_id),
            branch_id=str(bible.branch_id),
            settings=[SettingDTO.from_entity(s) for s in bible.settings],
            lore=[LoreDTO.from_entity(l) for l in bible.lore],
            created_at=bible.created_at,
            updated_at=bible.updated_at,
        )


class BibleListItemDTO(BaseModel):
    """DTO for bible list item (lightweight)."""

    id: str
    novel_id: str
    branch_id: str
    settings_count: int
    lore_count: int
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, bible: "WorldBible") -> "BibleListItemDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(bible.id),
            novel_id=str(bible.novel_id),
            branch_id=str(bible.branch_id),
            settings_count=len(bible.settings),
            lore_count=len(bible.lore),
            created_at=bible.created_at,
            updated_at=bible.updated_at,
        )