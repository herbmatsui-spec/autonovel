"""Social Media-style Narrative Relationship Models (Step 45)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ReactionType = Literal["empathy", "conflict", "irony", "support", "suspicion"]


class JournalEntry(BaseModel):
    """Character internal monologue or journal written after a scene."""

    entry_id: str = Field(description="Unique journal identifier")
    book_id: int = Field(default=1, description="Associated book ID")
    ep_num: int = Field(default=1, description="Associated episode number")
    scene_id: str = Field(default="", description="Scene reference")
    character_id: str = Field(description="Author character ID")
    character_name: str = Field(description="Author character name")
    theme: str = Field(default="", description="Core theme or topic of the journal")
    emotion: str = Field(default="", description="Primary emotion (e.g. jealousy, relief, suspicion)")
    content: str = Field(description="Internal monologue or journal body")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SocialComment(BaseModel):
    """Reaction / comment from another character onto a journal entry."""

    comment_id: str = Field(description="Unique comment identifier")
    journal_id: str = Field(description="Target journal entry ID")
    from_character_id: str = Field(description="Commenting character ID")
    from_character_name: str = Field(description="Commenting character name")
    reaction_type: ReactionType = Field(default="empathy", description="Nature of psychological reaction")
    content: str = Field(description="Comment or simulated psychological reaction text")
    trust_delta: float = Field(default=0.0, description="Change in trust metric (-100.0 to +100.0)")
    tension_delta: float = Field(default=0.0, description="Change in tension metric (-100.0 to +100.0)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RelationshipMetrics(BaseModel):
    """Dynamic relationship score between two characters."""

    char_a: str = Field(description="Character A ID or name")
    char_b: str = Field(description="Character B ID or name")
    trust_score: float = Field(default=50.0, ge=0.0, le=100.0, description="Trust (0-100)")
    tension_score: float = Field(default=50.0, ge=0.0, le=100.0, description="Tension (0-100)")
    affinity_score: float = Field(default=50.0, ge=0.0, le=100.0, description="Affinity (0-100)")
    last_interaction_ep: int = Field(default=1, description="Episode of last interaction")


__all__ = [
    "ReactionType",
    "JournalEntry",
    "SocialComment",
    "RelationshipMetrics",
]
