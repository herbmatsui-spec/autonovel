"""Domain models for the Arbitrator integration layer."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from src.narrative_balancer.models import Beat, CorrectionAction, ValidationResult


class PlotState(BaseModel):
    """Encapsulates current narrative state across all episodes."""
    model_config = ConfigDict(extra="ignore")

    total_episodes: int = Field(default=40, ge=1)
    beats: List[Beat] = Field(default_factory=list)
    characters: List[str] = Field(default_factory=lambda: ["Protagonist", "Rival", "Mentor"])
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_beats(cls, beats: List[Beat], total_episodes: Optional[int] = None) -> "PlotState":
        total = total_episodes or (max((b.episode for b in beats), default=40))
        return cls(total_episodes=total, beats=sorted(beats, key=lambda b: b.episode))

    def get_beat(self, episode: int) -> Optional[Beat]:
        for b in self.beats:
            if b.episode == episode:
                return b
        return None


class BalancerResult(BaseModel):
    """Output from an individual narrative balancer."""
    model_config = ConfigDict(extra="ignore")

    balancer_name: str
    beats: List[Beat] = Field(default_factory=list)
    actions: List[CorrectionAction] = Field(default_factory=list)
    detections_count: int = 0
    confidence: float = 1.0
    elapsed_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None


class ConflictRecord(BaseModel):
    """Records a resolved conflict between multiple balancers at an episode."""
    model_config = ConfigDict(extra="ignore")

    episode: int
    conflicting_balancers: List[str] = Field(default_factory=list)
    winning_balancer: str
    chosen_action: CorrectionAction
    superseded_actions: List[CorrectionAction] = Field(default_factory=list)
    rationale: str = ""


class IntegratedResult(BaseModel):
    """Final unified output from the GlobalNarrativeBalancer."""
    model_config = ConfigDict(extra="ignore")

    balanced_beats: List[Beat] = Field(default_factory=list)
    applied_actions: List[CorrectionAction] = Field(default_factory=list)
    conflicts: List[ConflictRecord] = Field(default_factory=list)
    balancer_results: Dict[str, BalancerResult] = Field(default_factory=dict)
    total_elapsed_ms: float = 0.0
    is_valid: bool = True
    validation_report: Optional[ValidationResult] = None
