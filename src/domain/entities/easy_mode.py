"""かんたんモード用ドメインエンティティおよびスキーマ定義。"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CharacterParams(BaseModel):
    """キャラクター設定パラメータ。"""

    name: str = Field(default="", max_length=100)
    personality: str = Field(default="", max_length=500)
    ability: str = Field(default="", max_length=500)
    genre: str = Field(default="", max_length=100)
    style_id: str | None = Field(default=None, description="適用する文体スタイルID")


class LLMConfigOverride(BaseModel):
    """オプトインでフロントエンドから渡されるLLM設定。"""

    provider: str | None = Field(default=None, description="gemini / openai / mock")
    api_key: str | None = Field(default=None, description="カスタムAPIキー")
    model_name: str | None = Field(default=None, description="モデル名 (例: gemini-2.5-flash, gpt-4o-mini)")
    base_url: str | None = Field(default=None, description="OpenAI互換 Base URL")


class EasyModeInput(BaseModel):
    """かんたんモード生成リクエスト入力。"""

    chapter_history: list[str] = Field(default_factory=list)
    current_chapter: str = ""
    character_params: CharacterParams = Field(default_factory=CharacterParams)
    content_length_limit: int = Field(default=2000, ge=1, le=10000)
    target_episodes: int = Field(default=1, ge=1, le=50, description="目標話数 (1〜50)")
    style_override: dict[str, Any] | None = Field(
        default=None, description="カスタムStyleProfileの辞書"
    )
    llm_config: LLMConfigOverride | None = Field(
        default=None, description="オプトインのLLM設定"
    )




class StreamQueryInput(BaseModel):
    """GET /easy_mode/generate/stream 用のクエリ互換入力。

    全フィールド Optional。空文字・空リストは EasyModeInput のデフォルトとして扱う。
    EventSource がクエリ文字列しか送れないため、本クラスで受け取った後に
    EasyModeInput に詰め替える。
    """

    chapter_history: list[str] | None = None
    current_chapter: str | None = None
    character_name: str | None = None
    character_personality: str | None = None
    character_ability: str | None = None
    character_genre: str | None = None
    content_length_limit: int | None = Field(default=None, ge=1, le=10000)

    def to_easy_mode_input(self) -> EasyModeInput:
        """クエリ入力を EasyModeInput に変換する。"""
        char = CharacterParams(
            name=self.character_name or "",
            personality=self.character_personality or "",
            ability=self.character_ability or "",
            genre=self.character_genre or "",
        )
        return EasyModeInput(
            chapter_history=self.chapter_history or [],
            current_chapter=self.current_chapter or "",
            character_params=char,
            content_length_limit=self.content_length_limit or 2000,
        )


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
    keywords: list[str] = Field(..., description="キーワードリスト", min_length=1)
    temperature: float = Field(0.7, description="生成の温度感")


class GachaResponse(BaseModel):
    request_id: str = Field(..., description="ガチャリクエスト全体のID")
    plans: list[GachaPlan] = Field(
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


class ReversePlotGeneratePayload(BaseModel):
    """逆算プロット生成リクエスト（APIキー不要のかんたんモード・UI用）"""
    answers: dict[str, Any] = Field(default_factory=dict, description="4ステップ回答")
    target_episodes: int = Field(default=10, ge=1, le=50, alias="targetEpisodes", description="目標話数")
    genre: str = Field(default="ハイファンタジー (R15)", description="ジャンル")
    llm_config: LLMConfigOverride | None = Field(default=None, description="オプトインのLLM設定")

    model_config = {"populate_by_name": True}


class ExportRequestPayload(BaseModel):
    """エクスポート用即時反映ペイロード"""
    title: str = Field(default="R15ファンタジー作品", description="タイトル")
    genre: str = Field(default="ファンタジー (R15)", description="ジャンル")
    current_text: str = Field(default="", description="画面上の最新本文")
    character: dict[str, Any] = Field(default_factory=dict, description="主人公設定")
    plots: list[dict[str, Any]] = Field(default_factory=list, description="プロット概要リスト")


class FullAutoRequest(BaseModel):
    """全自動生成リクエスト（かんたんモード・完全自律）"""
    api_key: str = Field(..., description="APIキー")
    genre: str = Field(default="ファンタジー", description="ジャンル")
    keywords: list[str] = Field(default_factory=list, description="キーワードリスト")
    protagonist_type: str = Field(default="チート主人公", description="主人公タイプ")
    target_episodes: int = Field(default=10, ge=1, le=50, description="目標話数")
    words_per_episode: int = Field(default=2000, ge=500, le=10000, description="話あたりの目標文字数")
    enable_audit: bool = Field(default=True, description="推敲監査を有効化")
    max_rewrites: int = Field(default=2, ge=0, le=5, description="最大リライト回数")


__all__ = [
    "CharacterParams",
    "LLMConfigOverride",
    "EasyModeInput",
    "StreamQueryInput",
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
    "ReversePlotGeneratePayload",
    "ExportRequestPayload",
    "FullAutoRequest",
]

