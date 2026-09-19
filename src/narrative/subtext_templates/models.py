"""
Data models for subtext template library (PLAN_Y2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TemplateMetadata(BaseModel):
    """Frontmatter metadata schema for subtext templates."""
    id: str = Field(..., description="Unique template identifier (e.g. betrayal.cold_acceptance)")
    category: str = Field(default="", description="Category (betrayal, grief, power_play, etc.)")
    tags: List[str] = Field(default_factory=list, description="Categorical and thematic tags")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Matching conditions: emotion, power_dynamic, relationship, intensity"
    )
    variables: List[Any] = Field(default_factory=list, description="Required or optional template variables")
    weight: int = Field(default=100, description="Base selection weight")
    final: bool = Field(default=False, description="Prioritize and stop subsequent matching")


class TemplateCandidate(BaseModel):
    """Candidate template matching given context."""
    id: str
    metadata: TemplateMetadata
    score: float = 1.0
    template_content: str = ""
    file_path: Optional[str] = None


class RenderedLine(BaseModel):
    """A line of rendered dialogue, beat, or stage action."""
    speaker: str = ""
    text: str = ""
    type: str = "dialogue"  # dialogue, beat, action


class RenderedDialogue(BaseModel):
    """Result of template rendering."""
    template_id: str
    lines: List[RenderedLine] = Field(default_factory=list)
    raw_text: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)
