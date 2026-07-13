from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from src.models.base import MODEL_CONFIG_DEFAULTS
from src.models.world import WorldState


class EpisodeDraft(BaseModel):
    ep_num:                  int             = Field(default=0)
    anti_pattern_prediction: str             = Field(default="")
    initial_manuscript:      str             = Field(default="")
    entertainment_audit:     str             = Field(default="")
    audit_checklist:         Dict[str, bool] = Field(default_factory=dict)
    final_content:           str             = Field(default="")
    candidates:              List[EpisodeDraft] = Field(default_factory=list, description="AIが提示した複数の本文候補案")
    self_critique:           str             = Field(default="")
    summary:                 str             = Field(default="")
    tension_delta:           int             = Field(default=0)
    love_delta:              int             = Field(default=0)
    next_world_state:        WorldState      = Field(default_factory=WorldState)
    cost_consumed:           int             = Field(default=0)

    @model_validator(mode="before")
    @classmethod
    def unwrap_draft_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "draft", "results"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class CharacterStatusChange(BaseModel):
    character: str = Field(..., description="キャラクター名")
    location: str = Field(..., description="現在の居場所")
    inventory_changes: List[str] = Field(default_factory=list, description="持ち物の変化（例: ['剣を失った', '聖杯を得た']）")
    status: str = Field(..., description="現在のステータス（生存/死亡/負傷/封印など）")

class EpisodeMetadata(BaseModel):
    title: str = Field(default="", description="エピソードのサブタイトル")
    summary: str = Field(default="", description="エピソードの簡潔なあらすじ")
    tension_delta: int = Field(default=0, description="この話での緊張・摩擦の変化量")
    qol_delta: int = Field(default=0, description="この話でのQOL（生活の質）変化量")
    love_delta: int = Field(default=0, description="この話でのヒロイン等の好感度変化量")
    ai_insight: str = Field(default="", description="確定した事実や設定の変更、伏線の回収状況に関するメモ")
    next_world_state: WorldState = Field(default_factory=WorldState, description="次のエピソード開始時の世界の状態メタデータ")
    character_status_changes: List[CharacterStatusChange] = Field(default_factory=list, description="この話で発生した各キャラのステータス変更（生死、所持品、位置）")


    model_config = MODEL_CONFIG_DEFAULTS

class EpisodeFinalDraft(BaseModel):
    ep_num:          int        = Field(...)
    final_content:   str        = Field(..., description="コンテと台本を統合した決定稿")
    summary:         str        = Field(default="")
    tension_delta:   int        = Field(default=0)
    love_delta:      int        = Field(default=0)
    next_world_state: WorldState = Field(default_factory=WorldState)

    model_config = MODEL_CONFIG_DEFAULTS

class StyleDNA(BaseModel):
    name:        str = Field(default="")
    instruction: str = Field(default="")

    model_config = MODEL_CONFIG_DEFAULTS

class StyleFragment(BaseModel):
    """RAG用：覇権作品の文体断片データ"""
    id: Optional[int] = None
    tag: str = Field(..., description="シーン属性（戦闘、心理、逆転、濡れ場等）")
    content: str = Field(..., description="理想的な文章の断片（100-500文字）")
    embedding_json: Optional[str] = Field(default=None, description="ベクトルデータ（JSON）")
    origin: str = Field(default="Masterpiece", description="出典元")

    model_config = MODEL_CONFIG_DEFAULTS

class MarketingPack(BaseModel):
    catchphrase:    str       = Field(default="")
    kakuyomu_notes: str       = Field(default="")
    tags:           List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_marketing_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "marketing", "pack"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS

# --- Phase 4: Pydantic models for Writing Context and Workflow Results ---
from src.models.db import BibleDbModel, BookDbModel, CharacterDbModel, PlotDbModel


class WritingContext(BaseModel):
    book: Optional[BookDbModel] = None
    plot: Optional[PlotDbModel] = None
    bible: Optional[BibleDbModel] = None
    chars: List[CharacterDbModel] = Field(default_factory=list)
    prev_ctx: str = ""
    static_ctx: str = ""
    dynamic_ctx: str = ""
    current_tension: int = 0
    genre_str: str = "fantasy"
    prev_integrity: int = 100
    prev_world_state: Dict[str, Any] = Field(default_factory=dict)
    pacing: Dict[str, Any] = Field(default_factory=dict)

    target_word_count: int = 2000
    tone_instruction: Dict[str, Any] = Field(default_factory=dict)
    sanitizer_policy: Dict[str, Any] = Field(default_factory=dict)
    masterpiece_guidance: str = ""
    prompt_patch: str = ""
    memories: str = ""
    prose_samples: List[Any] = Field(default_factory=list)
    dna_samples: List[Any] = Field(default_factory=list)
    engine_key: str = ""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    model_config = MODEL_CONFIG_DEFAULTS

class FullAutoWorkflowResult(BaseModel):
    book_id: Optional[int] = None
    title: str = ""
    chars_count: int = 0
    failed_episodes: List[Dict[str, Any]] = Field(default_factory=list)
    zip_data: Optional[bytes] = None
    zip_filename: Optional[str] = None
    status: str = "success"
    easy_parameters: Optional[Dict[str, Any]] = None

    model_config = MODEL_CONFIG_DEFAULTS

class PlanGenerationResult(BaseModel):
    book_id: int
    title: str

    model_config = MODEL_CONFIG_DEFAULTS

class PlotExpansionResult(BaseModel):
    count: int

    model_config = MODEL_CONFIG_DEFAULTS

class RetryFailedEpisodesResult(BaseModel):
    book_id: int
    chars_count: int
    failed_episodes: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS

class EpisodeWritingResult(BaseModel):
    book_id: int
    chars_count: int
    failed_episodes: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS

class PlotRebuildResult(BaseModel):
    done: bool
    count: int

    model_config = MODEL_CONFIG_DEFAULTS
