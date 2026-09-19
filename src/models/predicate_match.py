"""Data models for syntactic predicate analysis of foreshadowing keywords."""

from typing import List, Literal
from pydantic import BaseModel, Field


class PredicateMatch(BaseModel):
    """Represents a syntactic match between a foreshadowing keyword and an associated predicate."""

    keyword: str = Field(
        ...,
        description="Foreshadowing keyword found in the text",
    )
    predicate: str = Field(
        ...,
        description="Dictionary form of the predicate (verb/adjective) syntactically related to the keyword",
    )
    predicate_type: Literal["resolved", "progressed", "mention_only", "unknown"] = Field(
        ...,
        description="Classification of the predicate",
    )
    sentence: str = Field(
        ...,
        description="The full sentence where the match was identified",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this syntactic predicate match",
    )


class PredicateAnalysisResult(BaseModel):
    """Aggregate syntactic analysis result for a single foreshadowing entity."""

    foreshadowing_id: int = Field(
        ...,
        description="ID of the foreshadowing entity analyzed",
    )
    matches: List[PredicateMatch] = Field(
        default_factory=list,
        description="List of syntactic matches found for this foreshadowing",
    )
    highest_action: Literal["resolved", "progressed", "mention_only", "none"] = Field(
        default="none",
        description="Highest level action derived from the syntactic matches",
    )
    syntax_score: int = Field(
        default=0,
        ge=0,
        le=25,
        description="Calculated syntax score between 0 and 25 for ensemble voting",
    )
