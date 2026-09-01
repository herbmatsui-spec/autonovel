"""かんたんモード用 Pydantic スキーマ定義。"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CharacterParams(BaseModel):
    """キャラクター設定パラメータ。"""

    name: str = Field(default="", max_length=100)
    personality: str = Field(default="", max_length=500)
    ability: str = Field(default="", max_length=500)
    genre: str = Field(default="", max_length=100)


class EasyModeInput(BaseModel):
    """かんたんモード生成リクエスト入力。"""

    chapter_history: list[str] = Field(default_factory=list)
    current_chapter: str = ""
    character_params: CharacterParams = Field(default_factory=CharacterParams)
    content_length_limit: int = Field(default=2000, ge=1, le=10000)


class GenerationResponse(BaseModel):
    """かんたんモード生成レスポンス。"""

    task_id: str | None = None
    output: str = ""
    completion_time_ms: int = 0
    error: str = ""
    suggestions: list[str] = Field(default_factory=list)


# --- ガチャ / ダイジェスト / 昇格 スキーマ ---

class GachaPlanType(str, Enum):
    ROYAL = "royal"  # 王道案
    CURVEBALL = "curveball"  # 変化球案
    DARK = "dark"  # ダーク案


class DigestStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GachaPlan(BaseModel):
    plan_id: str = Field(..., description="企画の一意のID")
    plan_type: GachaPlanType = Field(..., description="企画のタイプ")
    title: str = Field(..., description="タイトル案")
    logline: str = Field(..., description="1行あらすじ")
    protagonist_summary: str = Field(..., description="主人公の簡単な説明")
    charm_point: str = Field(..., description="この案の最大の魅力（アピールポイント）")


class GachaRequest(BaseModel):
    genre: str = Field(..., description="対象ジャンル", min_length=1)
    keywords: List[str] = Field(..., description="キーワードリスト", min_length=1)
    temperature: float = Field(0.7, description="生成の温度感")


class GachaResponse(BaseModel):
    request_id: str = Field(..., description="ガチャリクエスト全体のID")
    plans: List[GachaPlan] = Field(
        ..., description="生成された3つの企画案", min_length=3, max_length=3
    )


class DigestRequest(BaseModel):
    request_id: str = Field(..., description="元のガチャリクエストID")
    selected_plan_id: str = Field(..., description="ユーザーが選択した企画ID")


class DigestResponse(BaseModel):
    book_id: str = Field(..., description="新規作成された作品ID")
    title: str = Field(default="", description="タイトル")
    synopsis: str = Field(default="", description="全体あらすじ")
    episode_1_text: str = Field(default="", description="第1話の本文テキスト")
    climax_preview_text: str = Field(
        default="", description="クライマックス（見せ場）のプレビューテキスト"
    )
    status: DigestStatus = Field(default=DigestStatus.COMPLETED, description="生成ステータス")


class PromotionRequest(BaseModel):
    book_id: str = Field(..., description="対象の作品ID")


class PromotionResponse(BaseModel):
    success: bool = Field(..., description="昇格処理の成功有無")
    redirect_url: str = Field(..., description="フロントエンドが遷移すべき上級者モードのURLパス")
    state_token: str = Field(..., description="引き継ぎ用の状態トークン")


__all__ = [
    "CharacterParams",
    "EasyModeInput",
    "GenerationResponse",
    "GachaPlanType",
    "DigestStatus",
    "GachaPlan",
    "GachaRequest",
    "GachaResponse",
    "DigestRequest",
    "DigestResponse",
    "PromotionRequest",
    "PromotionResponse",
]
