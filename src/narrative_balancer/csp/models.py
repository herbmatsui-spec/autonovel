"""Domain models, enums and structures for CSP Narrative Balancer."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from src.narrative_balancer.models import Beat, BeatType, CorrectionAction


class CharRole(str, Enum):
    """Character narrative roles."""
    PROTAGONIST = "PROTAGONIST"
    RIVAL = "RIVAL"
    MENTOR = "MENTOR"
    ALLY = "ALLY"
    ANTAGONIST = "ANTAGONIST"


class ConstraintPriority(str, Enum):
    """Constraint enforcement level."""
    HARD = "HARD"
    SOFT_HIGH = "SOFT_HIGH"
    SOFT_MEDIUM = "SOFT_MEDIUM"
    SOFT_LOW = "SOFT_LOW"


class ConflictClause(BaseModel):
    """Diagnosed conflicting constraint clause in infeasible problems."""
    model_config = ConfigDict(extra="ignore")

    constraint_name: str
    episodes: List[int] = Field(default_factory=list)
    description: str
    suggested_relaxation: str
