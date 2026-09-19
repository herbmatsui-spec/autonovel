"""Models for LLM co-generation writing metadata."""

from typing import Literal
from pydantic import BaseModel, Field


class ForeshadowingReport(BaseModel):
    """Report from the LLM on actions taken regarding a foreshadowing item during writing."""

    foreshadowing_id: int = Field(
        ...,
        description="ID of the foreshadowing item",
    )
    action: Literal["resolved", "progressed", "mentioned_only"] = Field(
        ...,
        description="Action performed in this episode: 'resolved' (fully resolved), 'progressed' (developed/progressed), or 'mentioned_only' (incidental mention)",
    )
    rationale: str = Field(
        default="",
        description="Brief explanation of why this action applies based on the scene",
    )
    excerpt: str = Field(
        default="",
        description="Scene excerpt or quote depicting the foreshadowing action",
    )


class WritingMetadata(BaseModel):
    """Metadata output accompanying generated episode prose."""

    episode_number: int = Field(
        ...,
        description="Episode number being written",
    )
    foreshadowings: list[ForeshadowingReport] = Field(
        default_factory=list,
        description="Reports on foreshadowing items addressed in this episode",
    )
    word_count_estimate: int | None = Field(
        default=None,
        description="Estimated word count of the generated prose",
    )
    unresolved_notes: list[str] = Field(
        default_factory=list,
        description="Notes on foreshadowings or plot points intentionally left unresolved",
    )
