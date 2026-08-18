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
    affinity_score: float = Field(50.0, ge=0.0, le=100.0)
    dependency_score: float = Field(20.0, ge=0.0, le=100.0)
    current_mood: str = "neutral"
    recent_change: float = 0.0


# Feature 3: Scene Theme
class SceneTheme(BaseModel):
    theme_type: str = "default"  # dark, erotic, battle, warm, mysterious
    primary_color: str = "#3498db"
    background_color: str = "#ffffff"
    accent_color: str = "#e74c3c"
    ambient_mood: str = "standard"


# Feature 4: What-If Route
class WhatIfRequest(BaseModel):
    episode_id: Optional[str] = None
    choice_point: str
    novel_context: Optional[str] = None


class WhatIfResponse(BaseModel):
    choice_point: str
    alternative_snippet: str
    outcome_summary: str
    impact_level: str = "major"


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
