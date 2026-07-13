from __future__ import annotations

import logging
from typing import Annotated, Any, Dict, List, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

logger = logging.getLogger(__name__)

# --- Utilities ---
def extract_float(v: Any) -> float:
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        try: return float(v.replace(',', ''))
        except ValueError: return 0.0
    return 0.0

def extract_int(v: Any) -> int:
    if isinstance(v, int): return v
    if isinstance(v, float): return int(v)
    if isinstance(v, str):
        try: return int(float(v.replace(',', '')))
        except ValueError: return 0
    return 0

def ensure_str(v: Any) -> str:
    return str(v) if v is not None else ""

# --- Supporting Models ---
class CliffhangerDef(BaseModel):
    hook_text: str = Field(default="", description="次話への引き。読者の期待感を煽る具体的記述")
    tension_type: str = Field(default="Standard", description="引きの種類 (Cliffhanger, Question, Revelation, Emotional)")
    resolved_in_ep: Optional[int] = Field(default=None, description="回収予定話数")

def ensure_cliffhanger_obj(v: Any) -> Any:
    if isinstance(v, dict): return CliffhangerDef(**v)
    if isinstance(v, str): return CliffhangerDef(hook_text=v)
    return v

class ChainPhase(BaseModel):
    # Simplified for this file
    value: str = "Friction"

def normalize_chain_phase(v: Any) -> str:
    if isinstance(v, str): return v
    return "Friction"

class SceneBeat(BaseModel):
    beat_id: str = Field(..., description="ビートID")
    action: str = Field(..., description="具体的行動")
    intent: str = Field(..., description="意図・目的")
    outcome: str = Field(..., description="結果・結果")

class SceneBeatList(BaseModel):
    beats: List[SceneBeat] = Field(default_factory=list)
    @model_validator(mode="before")
    @classmethod
    def unwrap_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict) and "beats" in data: return data
        if isinstance(data, list): return {"beats": data}
        return data

class SceneBeatBlock(BaseModel):
    """シーンを構成する最小単位の行動（ビート）。文字列からの自動変換に対応。"""
    @model_validator(mode="before")
    @classmethod
    def from_string(cls, data: Any) -> Any:
        if isinstance(data, str): return {"action": data}
        return data

class MasterSceneBlock(BaseModel):
    scene_number: int = Field(..., description="シーン番号", validation_alias=AliasChoices("scene_number", "scene_id", "no", "id"))
    scenes: List[SceneBeatBlock] = Field(default_factory=list, alias="beats")

    @field_validator("scenes", mode="before")
    @classmethod
    def ensure_beats_list(cls, v: Any) -> Any:
        if isinstance(v, list): return v
        if isinstance(v, dict) and "beats" in v: return v["beats"]
        return []

# --- Engine Architecture ---

from pydantic import ConfigDict

MODEL_CONFIG_DEFAULTS = ConfigDict(extra="allow")

class BaseEngine(BaseModel):
    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def get_routing_keys(cls) -> List[str]:
        """
        フラットなデータからこのモデルにルーティングすべきキーのリストを返す。
        デフォルトでは model_fields のキーをすべて返す。
        """
        return list(cls.model_fields.keys())

    @model_validator(mode="before")
    @classmethod
    def normalize_engine_data(cls, data: Any) -> Any:
        # サブクラスで個別の正規化ロジックを実装可能
        return data

class PlotCoreInfo(BaseModel):
    ep_num: int = Field(default=0, description="話数", validation_alias=AliasChoices("ep_num", "episode_num", "episode", "ep", "no", "number"))
    title: str = Field(default="", description="話題", validation_alias=AliasChoices("title", "episode_title"))

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def get_routing_keys(cls) -> List[str]:
        return ["ep_num", "episode_num", "episode", "ep", "no", "number", "title", "episode_title"]

class PlotAnalytics(BaseEngine):
    tension: Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="緊張感 (0-100)")
    tension_delta: Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="緊張感の変化量")
    catharsis: Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="カタルシス強度 (0-100)")
    is_catharsis: bool = Field(default=False, description="カタルシス発生回か")
    catharsis_type: str = Field(default="None", description="カタルシスの種類")
    emotional_payoff: str = Field(default="", description="感情的報酬の具体的内容")
    resolution_style: str = Field(default="", description="解決スタイル")
    antagonist_status: str = Field(default="", description="敵対者の状態")
    love_meter: Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="愛/信頼度の変動")

class PlotForeshadowing(BaseEngine):
    information_layers: Dict[str, List[str]] = Field(default_factory=dict, description="陣営別既知情報", validation_alias=AliasChoices("information_layers", "info_layers"))
    truth_ledger_updates: Dict[str, List[str]] = Field(default_factory=dict, description="新事実リスト", validation_alias=AliasChoices("truth_ledger_updates", "truth_updates"))
    knowledge_delta: Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="知識格差 (0.0-1.0)", validation_alias=AliasChoices("knowledge_delta", "intel_gap"))
    foreshadowing_refs: List[str] = Field(default_factory=list, description="伏線ID", validation_alias=AliasChoices("foreshadowing_refs", "refs"))
    truth_convergence: Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="真相収束度 (0.0-1.0)", validation_alias=AliasChoices("truth_convergence", "convergence"))
    knowledge_friction: Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="知識摩擦指数 (0.0-1.0)", validation_alias=AliasChoices("knowledge_friction", "friction"))
    foreshadowing_ledger: List[Dict[str, Any]] = Field(default_factory=list, description="未回収伏線リスト", validation_alias=AliasChoices("foreshadowing_ledger", "ledger"))

class EnigmaAnalytics(PlotForeshadowing):
    pass

class ComfortAnalytics(BaseEngine):
    qol_delta: Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="QOL向上値")
    veneration_gain: Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="崇拝度上昇")
    fulfillment_delta: Dict[str, float] = Field(default_factory=dict, description="次元別充足向上")
    is_miracle_occurrence: bool = Field(default=False, description="奇跡として誤認されたか")
    discovery_item: Optional[str] = Field(default=None, description="新発見/発明物")
    sanctuary_event: Optional[str] = Field(default=None, description="聖域イベント")

# --- Mixins ---

class CoreEngineMixin(BaseModel):
    core_info: PlotCoreInfo = Field(default_factory=PlotCoreInfo)
    analytics: PlotAnalytics = Field(default_factory=PlotAnalytics)
    foreshadowing: PlotForeshadowing = Field(default_factory=PlotForeshadowing)
    extra_engines: Dict[str, Any] = Field(default_factory=dict, description="未知・追加エンジンのデータスロット")

class EnigmaMixin(BaseModel):
    enigma: EnigmaAnalytics = Field(default_factory=EnigmaAnalytics)

class ComfortMixin(BaseModel):
    comfort: ComfortAnalytics = Field(default_factory=ComfortAnalytics)

# --- Episode Models ---

class PlotEpisodeBase(CoreEngineMixin):
    @classmethod
    def _get_sub_model_names(cls) -> List[str]:
        names = []
        for k, v in cls.model_fields.items():
            ann = v.annotation
            try:
                if isinstance(ann, type) and (issubclass(ann, BaseEngine) or issubclass(ann, PlotCoreInfo)):
                    names.append(k)
            except TypeError:
                pass
        return names

    @model_validator(mode="before")
    @classmethod
    def unwrap_plot_metadata(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # 1. Wrapper peeling
        for wrapper in ["metadata", "data", "plot", "episode", "results"]:
            if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                data = data[wrapper]
                break

        # 2. Dynamic Routing
        sub_models_names = cls._get_sub_model_names()
        for sub_name in sub_models_names:
            model_cls = cls.model_fields[sub_name].annotation
            if sub_name in data and isinstance(data[sub_name], dict):
                continue

            # Routing keys based on the sub-model
            routing_keys = getattr(model_cls, "get_routing_keys", lambda: list(model_cls.model_fields.keys()))()
            extracted_data = {k: data[k] for k in routing_keys if k in data}
            if extracted_data:
                data[sub_name] = extracted_data
                # ルーティングに使用したキーを data から削除して、後で extra_engines に混入させない
                for k in routing_keys:
                    if k in data:
                        data.pop(k)

        # 3. Extra Engines Collection
        # 動的ルーティングで data から pop したキーはすでに消えているため、
        # 現時点で data に残っている「未知のキー」を抽出する。
        all_routed_keys = set()
        for sub_name in sub_models_names:
            all_routed_keys.add(sub_name)

        generic_fields = {
            "next_hook", "misunderstanding_gap", "scenes", "script_content",
            "current_chain_phase", "burned_cost_or_loot", "thematic_milestone",
            "healed_fields", "is_micro_catharsis", "information_asymmetry_level",
            "lite_model_director_notes", "emotional_resonance_score",
            "thematic_depth_score", "literary_beauty_score"
        }

        # data に残っているキーのうち、汎用フィールドとサブモデル名、および extra_engines 自体を除外して抽出
        current_keys = list(data.keys())
        remaining_keys = [k for k in current_keys if k not in generic_fields and k not in sub_models_names and k != "extra_engines"]

        if remaining_keys:
            extra = {}
            for k in remaining_keys:
                extra[k] = data.pop(k)

            existing_extra = data.get("extra_engines", {})
            if not isinstance(existing_extra, dict):
                existing_extra = {}
            data["extra_engines"] = {**existing_extra, **extra}

        return data

class PlotEpisode(PlotEpisodeBase, EnigmaMixin, ComfortMixin):
    next_hook: Annotated[CliffhangerDef, BeforeValidator(ensure_cliffhanger_obj)] = Field(default_factory=CliffhangerDef, validation_alias=AliasChoices("next_hook", "cliffhanger", "hook"))
    misunderstanding_gap: str = Field(default="", validation_alias=AliasChoices("misunderstanding_gap", "gap", "irony"))
    scenes: List[MasterSceneBlock] = Field(default_factory=list)
    script_content: str = Field(default="", validation_alias=AliasChoices("script_content", "script", "manuscript", "content", "final_content"))
    current_chain_phase: Annotated[str, BeforeValidator(normalize_chain_phase)] = Field(default="Friction", validation_alias=AliasChoices("current_chain_phase", "phase", "chain_phase"))
    burned_cost_or_loot: Annotated[str, BeforeValidator(ensure_str)] = Field(default="なし", validation_alias=AliasChoices("burned_cost_or_loot", "cost", "loot"))
    thematic_milestone: str = Field(default="なし", validation_alias=AliasChoices("thematic_milestone", "milestone"))
    healed_fields: List[str] = Field(default_factory=list)
    is_micro_catharsis: bool = Field(default=False)
    information_asymmetry_level: Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0)
    lite_model_director_notes: str = Field(default="", validation_alias=AliasChoices("lite_model_director_notes", "self_critique", "director_notes", "notes"))
    emotional_resonance_score: Annotated[int, BeforeValidator(extract_int)] = Field(default=0)
    thematic_depth_score: Annotated[int, BeforeValidator(extract_int)] = Field(default=0)
    literary_beauty_score: Annotated[int, BeforeValidator(extract_int)] = Field(default=0)
    target_tension: Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="動的目標テンション値")

    @model_validator(mode="before")
    @classmethod
    def validate_plot(cls, data: Any) -> Any:
        return cls.unwrap_plot_metadata(data)

    @model_serializer(mode="wrap")
    def serialize_flat(self, handler) -> Dict[str, Any]:
        # Implement flattening if needed for API/DB
        return handler(self)

    def __getattr__(self, item: str) -> Any:
        if item == "self_critique": return self.lite_model_director_notes
        try:
            return getattr(self.analytics, item)
        except AttributeError:
            try:
                return getattr(self.foreshadowing, item)
            except AttributeError:
                return self.extra_engines.get(item)

def plot_episode_factory(genre: str, **data) -> PlotEpisode:
    genre_map = {
        "mystery": MysteryEpisode,
        "slice_of_life": SliceOfLifeEpisode,
        "drama": DramaEpisode,
    }
    model_cls = genre_map.get(genre.lower(), PlotEpisode)
    return model_cls(**data)

class MysteryEpisode(PlotEpisodeBase, EnigmaMixin):
    # Shared fields with PlotEpisode for compatibility
    next_hook: Annotated[CliffhangerDef, BeforeValidator(ensure_cliffhanger_obj)] = Field(default_factory=CliffhangerDef)
    script_content: str = Field(default="")
    # ... add other needed fields from PlotEpisode
    @model_validator(mode="before")
    @classmethod
    def validate_plot(cls, data: Any) -> Any:
        return cls.unwrap_plot_metadata(data)

class SliceOfLifeEpisode(PlotEpisodeBase, ComfortMixin):
    next_hook: Annotated[CliffhangerDef, BeforeValidator(ensure_cliffhanger_obj)] = Field(default_factory=CliffhangerDef)
    script_content: str = Field(default="")
    @model_validator(mode="before")
    @classmethod
    def validate_plot(cls, data: Any) -> Any:
        return cls.unwrap_plot_metadata(data)

class DramaEpisode(PlotEpisodeBase, EnigmaMixin, ComfortMixin):
    next_hook: Annotated[CliffhangerDef, BeforeValidator(ensure_cliffhanger_obj)] = Field(default_factory=CliffhangerDef)
    script_content: str = Field(default="")
    @model_validator(mode="before")
    @classmethod
    def validate_plot(cls, data: Any) -> Any:
        return cls.unwrap_plot_metadata(data)

