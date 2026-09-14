"""Chapter DTOs."""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class CreateChapterDTO(BaseModel):
    """DTO for creating a new chapter."""

    novel_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    episode_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=200)

    model_config = MODEL_CONFIG_DEFAULTS


class UpdateChapterDTO(BaseModel):
    """DTO for updating a chapter."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = None
    score_story: Optional[int] = Field(default=None, ge=0, le=100)
    killer_phrase: Optional[str] = None
    summary: Optional[str] = None
    world_state: Optional[str] = None
    trinity_review_log: Optional[str] = None
    ai_insight: Optional[str] = None
    tension_delta: Optional[int] = None
    qol_delta: Optional[int] = None
    is_anchor: Optional[bool] = None

    model_config = MODEL_CONFIG_DEFAULTS


class ChapterResponseDTO(BaseModel):
    """DTO for chapter response."""

    id: str
    novel_id: str
    branch_id: str
    episode_number: int
    title: str
    content: str
    score_story: Optional[int] = None
    killer_phrase: str
    summary: str
    world_state: str
    trinity_review_log: str
    ai_insight: str
    created_at: datetime
    tension_delta: int
    qol_delta: int
    is_anchor: bool

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, chapter: "Chapter") -> "ChapterResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(chapter.id),
            novel_id=str(chapter.novel_id),
            branch_id=str(chapter.branch_id),
            episode_number=chapter.episode_number,
            title=str(chapter.title),
            content=chapter.content,
            score_story=chapter.score_story,
            killer_phrase=chapter.killer_phrase,
            summary=chapter.summary,
            world_state=chapter.world_state,
            trinity_review_log=chapter.trinity_review_log,
            ai_insight=chapter.ai_insight,
            created_at=chapter.created_at,
            tension_delta=chapter.tension_delta,
            qol_delta=chapter.qol_delta,
            is_anchor=chapter.is_anchor,
        )


class ChapterListItemDTO(BaseModel):
    """DTO for chapter list item (lightweight)."""

    id: str
    novel_id: str
    branch_id: str
    episode_number: int
    title: str
    score_story: Optional[int] = None
    created_at: datetime
    is_anchor: bool

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, chapter: "Chapter") -> "ChapterListItemDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(chapter.id),
            novel_id=str(chapter.novel_id),
            branch_id=str(chapter.branch_id),
            episode_number=chapter.episode_number,
            title=str(chapter.title),
            score_story=chapter.score_story,
            created_at=chapter.created_at,
            is_anchor=chapter.is_anchor,
        )


class ReorderChaptersDTO(BaseModel):
    """DTO for reordering chapters."""

    chapter_orders: list[tuple[str, int]] = Field(..., min_length=1)
    # List of (chapter_id, new_episode_number)

    model_config = MODEL_CONFIG_DEFAULTS