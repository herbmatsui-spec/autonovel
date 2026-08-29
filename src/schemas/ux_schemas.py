from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Feature 1: Heatmap Data
class HeatmapPoint(BaseModel):
    position_pct: float = Field(..., ge=0.0, le=100.0, description="Position in story (0-100%)")
    tension: float = Field(0.0, ge=0.0, le=1.0, description="Tension score (0.0 - 1.0)")
    erotic: float = Field(0.0, ge=0.0, le=1.0, description="Erotic intensity (0.0 - 1.0)")
    hate: float = Field(0.0, ge=0.0, le=1.0, description="Hate / conflict score (0.0 - 1.0)")
    label: Optional[str] = Field(None, description="Beat or scene label")


class HeatmapData(BaseModel):
    episode_id: Optional[str] = None
    title: Optional[str] = None
    points: List[HeatmapPoint] = Field(default_factory=list)
    overall_pacing_score: float = 0.0


# Feature 2: Affinity Data
class AffinityData(BaseModel):
    character_name: str
    affinity_score: float = Field(50.0, ge=0.0, le=100.0, description="Affection score (0-100)")
    dependency_score: float = Field(20.0, ge=0.0, le=100.0, description="Dependency / Possessiveness score (0-100)")
    trust_score: float = Field(50.0, ge=0.0, le=100.0, description="Trust score (0-100)")
    wariness_score: float = Field(30.0, ge=0.0, le=100.0, description="Wariness / Psychological wall score (0-100)")
    current_mood: str = Field("neutral", description="Current mood / FSM stage (wary, observation, tsundere, affectionate, deep_love, neutral)")
    recent_change: float = 0.0

    @property
    def affection(self) -> float:
        return self.affinity_score

    @property
    def trust(self) -> float:
        return self.trust_score

    @property
    def dependency(self) -> float:
        return self.dependency_score

    @property
    def wariness(self) -> float:
        return self.wariness_score


# Feature 3: Scene Theme
class SceneTheme(BaseModel):
    theme_type: str = "default"  # dark, erotic, battle, warm, mysterious
    primary_color: str = "#3498db"
    background_color: str = "#ffffff"
    accent_color: str = "#e74c3c"
    ambient_mood: str = "standard"


class WhatIfRequest(BaseModel):
    episode_id: Optional[str] = None
    book_id: Optional[int] = None
    character_name: Optional[str] = None
    choice_point: str
    novel_context: Optional[str] = None


class WhatIfResponse(BaseModel):
    choice_point: str
    alternative_snippet: str
    outcome_summary: str
    impact_level: str = "major"
    branch_cache_key: Optional[str] = None


# Feature 4: Branch Forking & Multi-Ending Schemas
class BranchCreateRequest(BaseModel):
    book_id: int
    parent_branch_id: Optional[int] = 1
    fork_ep_num: int
    new_name: str
    divergence_reason: Optional[str] = ""
    what_if_snippet: Optional[str] = None


class BranchCreateResponse(BaseModel):
    branch_id: int
    book_id: int
    name: str
    parent_id: Optional[int]
    fork_ep_num: int
    divergence_reason: str
    status: str = "created"


# Feature 10: HITL (Human-in-the-Loop) Schemas
class HITLRequestPayload(BaseModel):
    session_id: str
    task_id: Optional[str] = None
    step_name: str
    prompt_preview: Optional[str] = None
    current_content: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    options: List[str] = Field(default_factory=list)
    timeout_seconds: int = 300


class HITLResumePayload(BaseModel):
    session_id: str
    approved: bool = True
    feedback: Optional[str] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)


# Feature 5: Dynamic Pacing / Reading Speed
class ReadingSpeedData(BaseModel):
    session_id: Optional[str] = None
    chars_read: int
    duration_ms: int
    scroll_speed_px_per_sec: float = 0.0
    suggested_metaphor_density: Optional[int] = 50


# Feature 6: Monologue / Afterglow
class MonologueResponse(BaseModel):
    character_name: str
    scene_type: str
    inner_monologue: str
    sentiment_tag: str = "vulnerable"


# Feature 7: Gap-Moe Preference
class GapMoePreference(BaseModel):
    gap_type: str = "tsundere"  # tsundere, kuudere_passionate, clumsy_genius, etc.
    intensity: int = Field(50, ge=0, le=100)
    target_character: Optional[str] = None


# Feature 8: Emotion Tags
class EmotionTag(BaseModel):
    text_segment: str
    emotion: str  # anger, sadness, joy, whisper, climax, shock
    animation_type: str  # shake, float, glow, typewriter, pulse


# Feature 9: Bedtime Supporter
class BedtimeMessage(BaseModel):
    character_name: str = "癒やしの案内人"
    message: str
    voice_tone: str = "gentle"
    ambient_theme: str = "midnight_stars"
