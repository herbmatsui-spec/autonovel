"""
マーケティング・タイトルCTR最大化モデル
PLAN 01: タイトル＆あらすじCTR爆発エンジン
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TitleCandidate(BaseModel):
    """生成されたタイトル候補とCTR予測結果"""

    title: str = Field(..., description="生成されたタイトル文字列")
    char_count: int = Field(..., description="文字数")
    syntax_type: str = Field(..., description="構文パターン名 (追放ざまぁ, 勘違い無双 等)")
    predicted_ctr_score: float = Field(..., ge=0.0, le=100.0, description="CTR予測スコア (0-100)")
    hooks: list[str] = Field(default_factory=list, description="含まれるフック要素")


class ViralTitleRequest(BaseModel):
    """バズタイトル生成リクエスト"""

    genre: str = Field(..., description="ジャンル (ファンタジー, 現代ドラマ 等)")
    core_concept: str = Field(..., description="作品の核心設定・独自性")
    protagonist_benefit: str = Field(..., description="主人公の圧倒的強み・実利")
    antagonist_misfortune: str = Field("", description="敵・元仲間へのざまぁ/見下し要素")
    candidate_count: int = Field(30, ge=10, le=50, description="生成候補数")


class ViralTitleResponse(BaseModel):
    """バズタイトル生成レスポンス"""

    top_recommendations: list[TitleCandidate] = Field(..., min_length=1, max_length=5, description="CTR最上位候補 (1-5案)")
    all_candidates: list[TitleCandidate] = Field(..., description="全生成候補")
    selected_synopsis: str = Field("", description="最上位タイトルに連動して生成されたあらすじ")
