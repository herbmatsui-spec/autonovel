"""Data models for ensemble foreshadowing resolution judgment."""

from typing import Literal
from pydantic import BaseModel, Field


class EnsembleScoreBreakdown(BaseModel):
    """Detailed score breakdown across the 3 non-LLM ensemble components."""

    contract_score: int = Field(
        default=0,
        ge=0,
        le=35,
        description="Beat-sheet contract score (0 or 35 points)",
    )
    metadata_score: int = Field(
        default=0,
        ge=0,
        le=40,
        description="LLM writing metadata self-report score (0, 20, or 40 points)",
    )
    syntax_score: int = Field(
        default=0,
        ge=0,
        le=25,
        description="Local syntactic morphology score (0 to 25 points)",
    )
    total_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Sum of all three scores (0 to 100 points)",
    )


class EnsembleJudgment(BaseModel):
    """Final ensemble decision for a foreshadowing item without extra LLM invocation."""

    foreshadowing_id: int = Field(
        ...,
        description="ID of the evaluated foreshadowing",
    )
    status: Literal["RESOLVED", "PROGRESSED", "PLANTED"] = Field(
        ...,
        description="Final lifecycle status: RESOLVED (>=75), PROGRESSED (35-74), or PLANTED (<35)",
    )
    score_breakdown: EnsembleScoreBreakdown = Field(
        ...,
        description="Detailed score breakdown",
    )
    rationale: str = Field(
        default="",
        description="Human-readable rationale synthesizing the ensemble decision",
    )
    should_reschedule: bool = Field(
        default=False,
        description="Whether this foreshadowing must be rescheduled for future episodes",
    )
