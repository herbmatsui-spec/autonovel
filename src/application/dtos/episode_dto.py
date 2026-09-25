"""Episode DTOs."""

from __future__ import annotations
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.novel import Episode

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class WriteEpisodeDTO(BaseModel):
    """DTO for writing a new episode."""

    novel_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    chapter_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    plot_summary: str = Field(default="")
    context: str = Field(default="")
    target_tension: int = Field(default=50, ge=0, le=100)
    target_catharsis: int = Field(default=0, ge=0, le=100)
    use_cache: bool = Field(default=False)
    use_semantic_cache: bool = Field(default=False)
    style_hint: str = Field(default="")

    model_config = MODEL_CONFIG_DEFAULTS


class RewriteEpisodeDTO(BaseModel):
    """DTO for rewriting an episode."""

    episode_id: str = Field(..., min_length=1)
    instructions: str = Field(..., min_length=1)
    target_tension: Optional[int] = Field(default=None, ge=0, le=100)
    target_catharsis: Optional[int] = Field(default=None, ge=0, le=100)
    preserve_killer_phrase: bool = Field(default=True)
    use_cache: bool = Field(default=False)
    use_semantic_cache: bool = Field(default=False)

    model_config = MODEL_CONFIG_DEFAULTS


class EpisodeResponseDTO(BaseModel):
    """DTO for episode response."""

    id: str
    novel_id: str
    branch_id: str
    number: int
    title: str
    content: str
    plot_summary: str
    tension: int
    catharsis: int
    status: str
    created_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, episode: "Episode") -> "EpisodeResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(episode.id),
            novel_id=str(episode.novel_id),
            branch_id=str(episode.branch_id),
            number=episode.number,
            title=str(episode.title),
            content=episode.content,
            plot_summary=episode.plot_summary,
            tension=episode.tension,
            catharsis=episode.catharsis,
            status=episode.status,
            created_at=episode.created_at,
        )


class EpisodeDraftDTO(BaseModel):
    """DTO for episode draft (in-progress)."""

    id: str
    novel_id: str
    branch_id: str
    number: int
    title: str
    content: str
    plot_summary: str
    tension: int
    catharsis: int
    status: str
    word_count: int
    last_saved_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, episode: "Episode") -> "EpisodeDraftDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(episode.id),
            novel_id=str(episode.novel_id),
            branch_id=str(episode.branch_id),
            number=episode.number,
            title=str(episode.title),
            content=episode.content,
            plot_summary=episode.plot_summary,
            tension=episode.tension,
            catharsis=episode.catharsis,
            status=episode.status,
            word_count=len(episode.content.split()) if episode.content else 0,
            last_saved_at=episode.created_at,
        )


class EpisodeListItemDTO(BaseModel):
    """DTO for episode list item (lightweight)."""

    id: str
    novel_id: str
    branch_id: str
    number: int
    title: str
    status: str
    tension: int
    catharsis: int
    created_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, episode: "Episode") -> "EpisodeListItemDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(episode.id),
            novel_id=str(episode.novel_id),
            branch_id=str(episode.branch_id),
            number=episode.number,
            title=str(episode.title),
            status=episode.status,
            tension=episode.tension,
            catharsis=episode.catharsis,
            created_at=episode.created_at,
        )


class ExpandPlotDTO(BaseModel):
    """DTO for expanding a plot point into episode."""

    plot_point_id: str = Field(..., min_length=1)
    novel_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    episode_number: int = Field(..., ge=1)
    detail_level: str = Field(default="normal")  # "brief", "normal", "detailed"

    model_config = MODEL_CONFIG_DEFAULTS
