"""Novel DTOs."""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.metadata import NovelStatus, NovelMode

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class CreateNovelDTO(BaseModel):
    """DTO for creating a new novel."""

    title: str = Field(..., min_length=1, max_length=200)
    author_id: str = Field(..., min_length=1)
    genre: str = Field(default="")
    catchcopy: str = Field(default="")
    synopsis: str = Field(default="")
    concept: str = Field(default="")
    target_episodes: int = Field(default=50, ge=1, le=500)
    mode: NovelMode = Field(default=NovelMode.EASY)

    model_config = MODEL_CONFIG_DEFAULTS


class UpdateNovelDTO(BaseModel):
    """DTO for updating a novel."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    genre: Optional[str] = None
    catchcopy: Optional[str] = None
    synopsis: Optional[str] = None
    concept: Optional[str] = None
    target_episodes: Optional[int] = Field(default=None, ge=1, le=500)
    style_dna: Optional[str] = None

    model_config = MODEL_CONFIG_DEFAULTS


class NovelResponseDTO(BaseModel):
    """DTO for novel response (single item)."""

    id: str
    title: str
    author_id: str
    genre: str
    catchcopy: str
    synopsis: str
    concept: str
    status: NovelStatus
    mode: NovelMode
    target_episodes: int
    style_dna: str
    created_at: datetime
    updated_at: datetime
    cumulative_tension: int
    cumulative_qol: int
    cumulative_cost: float
    cumulative_cost_tokens: int
    sanctuary_integrity: int
    current_branch_id: Optional[str] = None

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, novel: "Novel") -> "NovelResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(novel.id),
            title=str(novel.title),
            author_id=str(novel.author_id),
            genre=str(novel.genre),
            catchcopy=str(novel.catchcopy),
            synopsis=str(novel.synopsis),
            concept=str(novel.concept),
            status=novel.status,
            mode=novel.mode,
            target_episodes=novel.target_episodes,
            style_dna=novel.style_dna,
            created_at=novel.created_at,
            updated_at=novel.updated_at,
            cumulative_tension=novel.cumulative_tension,
            cumulative_qol=novel.cumulative_qol,
            cumulative_cost=novel.cumulative_cost.value,
            cumulative_cost_tokens=novel.cumulative_cost.tokens_used,
            sanctuary_integrity=novel.sanctuary_integrity,
            current_branch_id=str(novel.current_branch_id) if novel.current_branch_id else None,
        )


class NovelListItemDTO(BaseModel):
    """DTO for novel list item (lightweight)."""

    id: str
    title: str
    author_id: str
    genre: str
    status: NovelStatus
    mode: NovelMode
    target_episodes: int
    created_at: datetime
    updated_at: datetime
    cumulative_tension: int
    cumulative_qol: int

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, novel: "Novel") -> "NovelListItemDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(novel.id),
            title=str(novel.title),
            author_id=str(novel.author_id),
            genre=str(novel.genre),
            status=novel.status,
            mode=novel.mode,
            target_episodes=novel.target_episodes,
            created_at=novel.created_at,
            updated_at=novel.updated_at,
            cumulative_tension=novel.cumulative_tension,
            cumulative_qol=novel.cumulative_qol,
        )


class NovelSearchDTO(BaseModel):
    """DTO for novel search/filter parameters."""

    author_id: Optional[str] = None
    genre: Optional[str] = None
    status: Optional[NovelStatus] = None
    mode: Optional[NovelMode] = None
    title_contains: Optional[str] = None

    model_config = MODEL_CONFIG_DEFAULTS