from pydantic import BaseModel, Field


class BeatSheetItem(BaseModel):
    beat_number: int = Field(..., description="ビートの順番")
    description: str = Field(..., description="このビートで起こる出来事（3〜5行程度）")
    character_focus: list[str] = Field(default_factory=list, description="主要に動くキャラクター")


class BeatSheet(BaseModel):
    items: list[BeatSheetItem] = Field(..., description="ストーリーの起承転結を構成するビート群")
    summary: str = Field(..., description="この話の全体的な要約")


class EpisodeBeat(BaseModel):
    ep_num: int = Field(..., ge=1, le=40, description="話数 (1-40)")
    phase: str = Field(..., description="ビートシートのフェーズ (開幕フック、初期成功・拠点確立など)")
    mission: str = Field(..., description="その話の具体的なミッション・目的")
    tension_target: float = Field(..., ge=0.0, le=1.0, description="目標とするテンション値 (0.0-1.0)")
    visual_scene_focus: str = Field(..., description="コミカライズ時の見せ場・ビジュアルフォーカス")
    target_foreshadowing_ids: list[int] = Field(default_factory=list, description="本話で回収を試みる伏線IDリスト")


class PlotVariantScore(BaseModel):
    consistency_score: int = Field(..., ge=0, le=100)
    engagement_score: int = Field(..., ge=0, le=100)
    pacing_score: int = Field(..., ge=0, le=100)
    emotional_resonance_score: int = Field(
        default=50, ge=0, le=100, description="感情的共鳴・共感スコア (0-100)"
    )
    thematic_depth_score: int = Field(
        default=50, ge=0, le=100, description="テーマの深さ・哲学的問いスコア (0-100)"
    )
    literary_beauty_score: int = Field(
        default=50, ge=0, le=100, description="文章の美しさ・比喩の斬新さスコア (0-100)"
    )
    total_score: int = Field(..., ge=0, le=300)
    reasoning: str = Field(...)
