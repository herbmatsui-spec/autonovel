"""Common domain models for narrative tension balancers."""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BeatType(str, Enum):
    """Narrative beat types."""
    SETUP = "SETUP"
    RISING = "RISING"
    BATTLE = "BATTLE"
    DISASTER = "DISASTER"
    MIDPOINT_DISASTER = "MIDPOINT_DISASTER"
    PAYOFF = "PAYOFF"
    DAILY = "DAILY"
    RECOVERY = "RECOVERY"
    STAGNATION = "STAGNATION"
    FALLOUT = "FALLOUT"
    CLIMAX = "CLIMAX"
    RESOLUTION = "RESOLUTION"


class Beat(BaseModel):
    """Represents a single episode beat in the plot."""
    model_config = ConfigDict(extra="ignore")

    episode: int = Field(..., description="Episode index (1-based)")
    tension: Optional[float] = Field(default=5.0, description="Tension score between 0.0 and 10.0 (or None/NaN if missing)")
    beat_type: BeatType = Field(default=BeatType.SETUP, description="Structural beat type")
    title: str = Field(default="", description="Episode title")
    summary: str = Field(default="", description="Episode summary or key events")
    characters: List[str] = Field(default_factory=list, description="List of present characters")
    is_defeat: bool = Field(default=False, description="Whether protagonist suffers defeat")
    foreshadowing_setup: List[str] = Field(default_factory=list, description="Foreshadowing introduced in this episode")
    foreshadowing_payoff: List[str] = Field(default_factory=list, description="Foreshadowing resolved in this episode")


class CorrectionAction(BaseModel):
    """Recorded correction applied to an episode."""
    model_config = ConfigDict(extra="ignore")

    episode: int
    action_type: str = Field(..., description="E.g. TENSION_BOOST, BEAT_TYPE_CHANGE, INSERT_EVENT")
    target_field: str = Field(default="tension", description="Field modified")
    original_value: Any = None
    new_value: Any = None
    reason: str = Field(default="", description="Mathematical or grammatical rationale for correction")


class ValidationResult(BaseModel):
    """Structural validation outcome."""
    model_config = ConfigDict(extra="ignore")

    is_valid: bool = True
    violations: List[str] = Field(default_factory=list)
    score: float = Field(default=1.0, ge=0.0, le=1.0)
