from typing import List

from pydantic import BaseModel, Field


class BeatSheetItem(BaseModel):
    beat_number: int = Field(..., description="ビートの順番")
    description: str = Field(..., description="このビートで起こる出来事（3〜5行程度）")
    character_focus: List[str] = Field(default_factory=list, description="主要に動くキャラクター")

class BeatSheet(BaseModel):
    items: List[BeatSheetItem] = Field(..., description="ストーリーの起承転結を構成するビート群")
    summary: str = Field(..., description="この話の全体的な要約")

class PlotVariantScore(BaseModel):
    consistency_score: int = Field(..., ge=0, le=100)
    engagement_score: int = Field(..., ge=0, le=100)
    pacing_score: int = Field(..., ge=0, le=100)
    emotional_resonance_score: int = Field(default=50, ge=0, le=100, description="感情的共鳴・共感スコア (0-100)")
    thematic_depth_score:      int = Field(default=50, ge=0, le=100, description="テーマの深さ・哲学的問いスコア (0-100)")
    literary_beauty_score:     int = Field(default=50, ge=0, le=100, description="文章の美しさ・比喩の斬新さスコア (0-100)")
    total_score: int = Field(..., ge=0, le=300)
    reasoning: str = Field(...)
