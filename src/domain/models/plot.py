from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from src.domain.types import BookId


class PlotEpisode(BaseModel):
    """
    PlotEpisode ドメインエンティティ。
    エピソード単位のプロット詳細と分析データを保持する。
    """
    book_id: BookId
    branch_id: int
    ep_num: int
    title: str
    summary: str
    thought_process: str
    detailed_blueprint: str
    tension: int = Field(50, ge=0, le=100)
    tension_delta: int = 0
    catharsis: int = Field(0, ge=0, le=100)
    status: str = "planned"
    scenes: str = ""
    is_catharsis: bool = False
    catharsis_type: str = "なし"
    love_meter: int = Field(0, ge=0, le=100)
    next_hook: str = ""
    misunderstanding_gap: str = ""
    resolution_style: str = "Cheat"
    antagonist_status: str = "現状維持"
    emotional_resonance_score: int = Field(0, ge=0, le=100)
    thematic_depth_score: int = Field(0, ge=0, le=100)
    literary_beauty_score: int = Field(0, ge=0, le=100)
    # 拡張エンジン用データ (JSON文字列や辞書)
    extra_data: Dict[str, Any] = Field(default_factory=dict)

    def is_critical_episode(self) -> bool:
        """カタルシスが発生しているか、緊張感が極めて高いエピソードかを判定"""
        return self.is_catharsis or self.tension > 80
