from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Literal, Optional, Tuple

from pydantic import BaseModel, Field


@dataclass
class LLMRequestOptions:
    model_name: str
    prompt: str
    system_instruction: Optional[str] = None
    response_schema: Any = None
    temp: float = 0.7
    max_retries: int = 5
    stream_callback: Optional[Callable[[str], None]] = None
    reporter: Optional[Any] = None
    use_cache: bool = False
    use_semantic_cache: bool = False
    task_type: str = "general"
    genre: str = "general"
    difficulty: int = 50
    current_tension: int = 0
    expected_ep_num: Optional[int] = None
    cached_content: Optional[str] = None
    threshold: float = 0.95
    extra_kwargs: Dict[str, Any] = field(default_factory=dict)


# ==========================================
# Type Definitions / Enums
# ==========================================
ChainPhase = Literal["Friction", "Prep", "Payoff", "Discovery", "Bonding", "Fulfillment", "Hate"]

StyleKey = Literal["style_web_standard", "style_serious_fantasy", "style_psychological_loop",
                   "style_chat_log", "style_villainess_elegant", "style_military_rational",
                   "style_comedy_speed", "style_dark_hero", "style_overlord", "style_bookworm_daily", "style_light_fun"]

# Pydantic V2 internal configuration to prevent naming conflicts and allow 'model_' prefixes
from pydantic import ConfigDict

MODEL_CONFIG_DEFAULTS = ConfigDict(
    populate_by_name=True,
    extra="allow",
    protected_namespaces=()
)

# ==========================================
# 例外クラス (src.core.exceptions から統合)
# ==========================================
from src.core.exceptions import EngineError  # noqa: F401 - backward compat re-export

class GenerateResult(BaseModel):
    """AI生成結果を保持するコンテナ"""
    success: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    story_content: str = ""
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def unwrap_or(self, default_meta: Dict[str, Any], default_story: str) -> Tuple[Dict[str, Any], str]:
        """成功時は結果を、失敗時はデフォルト値を返す便利メソッド"""
        if self.success:
            return self.metadata, self.story_content
        return default_meta, default_story

    model_config = MODEL_CONFIG_DEFAULTS

# ==========================================
# Utility Functions
# ==========================================
def extract_int(v: Any) -> int:
    """文字列から数値を抽出する。'80%' -> 80, 'High (50)' -> 50, 'Extreme' -> 90等"""
    if isinstance(v, int):
        return v
    if not v or not isinstance(v, str):
        return 0

    # 特殊な単語の変換
    word_map = {
        "extreme": 90, "high": 70, "medium": 50, "low": 20, "none": 0, "very high": 85,
        "なし": 0, "低": 20, "中": 50, "高": 80, "最高": 100
    }
    v_lower = v.lower()
    for word, val in word_map.items():
        if word in v_lower:
            return val

    # 数値の抽出
    nums = re.findall(r'-?\d+', v)
    if nums:
        return int(nums[0])
    return 0

def normalize_chain_phase(v: Any) -> str:
    """ChainPhaseのゆらぎを補正する"""
    valid_phases = ["Friction", "Prep", "Payoff", "Discovery", "Bonding", "Fulfillment"]
    if v in valid_phases:
        return str(v)
    if not isinstance(v, str):
        return "Friction"
    v_lower = v.lower()
    if "friction" in v_lower or "軋轢" in v_lower or "hate" in v_lower or "ヘイト" in v_lower: return "Friction"
    if "prep" in v_lower or "準備" in v_lower: return "Prep"
    if "payoff" in v_lower or "カタルシス" in v_lower or "回収" in v_lower or "climax" in v_lower or "resolution" in v_lower: return "Payoff"
    if "discovery" in v_lower or "発見" in v_lower: return "Discovery"
    if "bonding" in v_lower or "絆" in v_lower or "交流" in v_lower: return "Bonding"
    if "fulfillment" in v_lower or "充足" in v_lower or "安らぎ" in v_lower: return "Fulfillment"
    return "Friction"

def ensure_str(v: Any) -> str:
    """文字列であることを保証する"""
    if isinstance(v, str):
        return v
    if v is None:
        return "なし"
    return str(v)


# ==========================================
# Mixins for Data Normalization
# ==========================================
class FlatModelMixin(BaseModel):
    """
    AIが生成したフラットなJSONデータを、
    Pydanticモデルの構造（ネストされたモデル等）に自動的にルーティングし、
    ラッパー（'metadata'や'data'キー）を除去するための共通Mixin。
    """

    @classmethod
    def unwrap_flat_metadata(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # 1. Wrapper peeling: 不要な外殻を除去
        for wrapper in ["metadata", "data", "results", "plot", "episode"]:
            if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                data = data[wrapper]
                break

        if not isinstance(data, dict):
            return data

        # 2. Dynamic Routing: サブモデル（BaseEngine継承クラス等）への自動振り分け
        # model_fields からサブモデル（BaseModel継承クラス）を抽出
        sub_model_fields = []
        for field_name, field_info in cls.model_fields.items():
            ann = field_info.annotation
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                sub_model_fields.append((field_name, ann))

        for sub_name, model_cls in sub_model_fields:
            # すでに正しい構造（辞書）でデータが入っている場合はスキップ
            if sub_name in data and isinstance(data[sub_name], dict):
                continue

            # モデルが get_routing_keys を持っていればそれを使い、なければフィールド名をすべて使う
            routing_keys = getattr(model_cls, "get_routing_keys", lambda: list(model_cls.model_fields.keys()))()

            # フラットなデータから対象キーを抽出
            extracted = {k: data[k] for k in routing_keys if k in data}
            if extracted:
                data[sub_name] = extracted
                # ルーティング済みのキーはルートから削除（extra_engines への混入防止）
                for k in routing_keys:
                    if k in data:
                        data.pop(k)

        return data

# ==========================================
# Gemini Schema Customization
# ==========================================
try:
    from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
    from pydantic_core import core_schema

    class GeminiSchemaGenerator(GenerateJsonSchema):
        """Gemini API非対応のキー(title, description, default, additionalProperties)を除去するPydantic用スキーマジェネレータ"""
        def generate(self, schema: core_schema.CoreSchema, mode: Literal['validation', 'serialization'] = 'validation') -> JsonSchemaValue:
            json_schema = super().generate(schema, mode=mode)
            return self._clean_schema(json_schema)

        def _clean_schema(self, obj: Any) -> JsonSchemaValue:
            if isinstance(obj, dict):
                cleaned = {}
                for k, v in obj.items():
                    if k in ("title", "description", "default", "additionalProperties", "additional_properties"):
                        continue
                    cleaned[k] = self._clean_schema(v)
                return cleaned
            elif isinstance(obj, list):
                return [self._clean_schema(item) for item in obj] # type: ignore
            return obj # type: ignore

    def get_gemini_schema(model_class: Any) -> Dict[str, Any]:
        """指定したPydanticモデルクラスのGemini用JSONスキーマを取得する"""
        if hasattr(model_class, "model_json_schema"):
            return model_class.model_json_schema(schema_generator=GeminiSchemaGenerator) # type: ignore
        return {}

except ImportError:
    # フォールバック (Pydantic v1互換やインポートエラー対策)
    def get_gemini_schema(model_class: Any) -> Dict[str, Any]:
        if hasattr(model_class, "model_json_schema"):
            return model_class.model_json_schema() # type: ignore
        return {}
