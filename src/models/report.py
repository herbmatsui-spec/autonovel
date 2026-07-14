"""
src/models/report.py — 制作レポート用データモデル
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TokenUsageReport(BaseModel):
    """トークン使用量レポート"""
    total_tokens: int = Field(default=0, description="総トークン数")
    input_tokens: int = Field(default=0, description="入力トークン数")
    output_tokens: int = Field(default=0, description="出力トークン数")
    episode_count: int = Field(default=0, description="生成エピソード数")
    generation_time_seconds: float = Field(default=0.0, description="生成所要時間（秒）")

    def add_usage(self, input_tokens: int, output_tokens: int):
        """使用量を加算"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens


class QualityMetricsReport(BaseModel):
    """品質メトリクスレポート"""
    coherence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="物語整合性スコア")
    character_consistency: float = Field(default=0.0, ge=0.0, le=1.0, description="キャラクター一貫性")
    pacing_score: float = Field(default=0.0, ge=0.0, le=1.0, description="ペーシングスコア")
    hook_retention: float = Field(default=0.0, ge=0.0, le=1.0, description="フック保持率")
    emotional_resonance: float = Field(default=0.0, ge=0.0, le=1.0, description="感情共鳴度")
    commercial_viability: float = Field(default=0.0, ge=0.0, le=1.0, description="商業的ポテンシャル")


class EpisodeSummary(BaseModel):
    """エピソードサマリー"""
    ep_num: int = Field(description="エピソード番号")
    title: str = Field(default="", description="話タイトル")
    word_count: int = Field(default=0, description="文字数")
    summary: str = Field(default="", description="要約（100文字程度）")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="品質スコア")


class ProductionReport(BaseModel):
    """制作レポート（完全版）"""
    title: str = Field(description="作品タイトル")
    genre: str = Field(description="ジャンル")
    target_word_count: int = Field(default=3000, description="目標文字数/話")
    token_usage: Optional[TokenUsageReport] = Field(default=None, description="トークン使用量")
    quality_metrics: Optional[QualityMetricsReport] = Field(default=None, description="品質メトリクス")
    episode_summaries: List[EpisodeSummary] = Field(default_factory=list, description="エピソード一覧")
    total_generation_time: float = Field(default=0.0, description="総生成時間（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "覇者の帰還",
                "genre": "fantasy",
                "target_word_count": 3000,
                "token_usage": {
                    "total_tokens": 150000,
                    "input_tokens": 80000,
                    "output_tokens": 70000,
                    "episode_count": 10,
                    "generation_time_seconds": 300.0
                },
                "quality_metrics": {
                    "coherence_score": 0.85,
                    "character_consistency": 0.90,
                    "pacing_score": 0.78,
                    "hook_retention": 0.82,
                    "emotional_resonance": 0.75,
                    "commercial_viability": 0.88
                },
                "episode_summaries": [],
                "total_generation_time": 300.0,
                "created_at": "2026-07-13T00:00:00"
            }
        }