from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)
from typing_extensions import Annotated

from src.models.base import (
    MODEL_CONFIG_DEFAULTS,
    ChainPhase,
    FlatModelMixin,
    ensure_str,
    extract_int,
    normalize_chain_phase,
)
from src.models.emotional_hook import EmotionalHookSpec
from src.models.sharp_edge import SharpEdgeSpec


class ReviewLog(BaseModel):
    plan_name:             str = Field(default="")
    experiment_1_score:    int = Field(default=0)
    experiment_1_comments: str = Field(default="")
    experiment_2_score:    int = Field(default=0)
    experiment_2_comments: str = Field(default="")

    model_config = MODEL_CONFIG_DEFAULTS

def extract_float(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.search(r'-?\d+\.\d+|-?\d+', v)
        if m:
            return float(m.group(0))
        ext = extract_int(v) if 'extract_int' in globals() else 0
        return float(ext) / 100.0 if ext > 0 else 0.0
    return 0.0

class DynamicPacing(BaseModel):
    ep_range:        str = Field(default="")
    phase_name:      str = Field(default="")
    required_events: str = Field(default="")

    model_config = MODEL_CONFIG_DEFAULTS

class SceneBeat(BaseModel):
    """プロットから分解された物理動作ビート"""
    beat_num: int = Field(..., description="ビート番号")
    physical_action: str = Field(..., description="肉体的な動作描写")
    sensory_tags: List[str] = Field(default_factory=list, description="五感タグ: smell, sound, touch, taste, sight")
    emotion_phase: str = Field(default="neutral", description="感情フェーズ: buildup/explosion/aftermath")
    word_budget: int = Field(default=200, description="このビートに配分する目標文字数")

    model_config = MODEL_CONFIG_DEFAULTS

class SceneBeatList(BaseModel):
    beats: List[SceneBeat] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "beats"]:
                if wrapper in data and isinstance(data[wrapper], list) and len(data) == 1:
                    data = {"beats": data[wrapper]}
                    break
                elif wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class CliffhangerDef(BaseModel):
    type:        str = Field(default="", description="New Crisis / Shocking Truth / Quiet Foreshadowing")
    description: str = Field(default="")

def ensure_cliffhanger_obj(v: Any) -> Any:
    if isinstance(v, str):
        return {"description": v, "type": "New Crisis"}
    return v

# AIが吐きがちな表現をLiteralにマッピングするヘルパー
def normalize_beat_type(v: Any) -> str:
    # 完全一致・部分一致の両方に対応した英語→日本語マッピング
    exact_mapping = {
        # 基本英語
        "Introduction": "導入", "Start": "導入", "Opening": "導入", "Setup": "導入",
        "In Medias Res": "導入", "Inciting Incident": "導入", "Inciting Event": "導入",
        "World Building": "導入", "World Building / Setup": "導入",
        "Development": "展開", "Rising": "展開", "Rising Action": "展開",
        "Escalation": "展開", "Revelation": "展開", "Exposure": "展開",
        "Ascension": "展開", "Strategic Realization": "展開", "Power Awakening": "展開",
        "Conflict / Humiliation": "展開",
        "Conclusion": "結末", "End": "結末", "Climax": "結末", "Resolution": "結末",
        "Climax of Scene": "結末", "Climax of Scene / Exile": "結末",
        "Bottoming Out": "結末", "Culmination": "結末", "Payoff": "結末",
        "Context": "状況", "Background": "状況", "Truth": "状況",
        "Revelation of Truth": "状況", "Environmental Horror": "状況", "Atmosphere": "状況",
        "Situation": "状況",
        "Internal": "内面葛藤", "Thought": "内面葛藤", "Internal Conflict": "内面葛藤",
        "Reflection": "内面葛藤", "Mental Reconstruction": "内面葛藤",
        "Physical and Mental Decay": "内面葛藤", "Conflict": "内面葛藤",
        "Tension": "内面葛藤", "Dilemma": "内面葛藤",
        "Action": "具体的行動", "Battle": "具体的行動", "Retribution": "具体的行動",
        "Vow of Revenge": "具体的行動", "Interaction": "具体的行動", "Confrontation": "具体的行動",
        "Decision": "具体的行動", "Physical Action": "具体的行動",
        "Aftermath": "余韻", "Cliffhanger": "余韻", "Denouement": "余韻",
        "Quiet Foreshadowing": "余韻", "Calm": "余韻", "Echo": "余韻",
    }
    if not isinstance(v, str):
        return str(v) if v is not None else "導入"

    # 完全一致チェック
    if v in exact_mapping:
        return exact_mapping[v]

    # 部分一致チェック（大文字小文字無視）
    v_lower = v.lower()
    # 誤マッチ（"Revelation of Truth" が "Revelation" に先に吸われる等）を防ぐため、文字数が長い順に評価
    for eng, jap in sorted(exact_mapping.items(), key=lambda x: len(x[0]), reverse=True):
        if eng.lower() in v_lower:
            return jap

    # 日本語有効値ならそのまま返す
    valid_jp = ["導入", "展開", "結末", "状況", "内面葛藤", "具体的行動", "余韻"]
    if v in valid_jp:
        return v

    # どれにも該当しなければデフォルト値（バリデーションエラーを防ぐ）
    return "導入"

BeatType = Annotated[
    Literal["導入", "展開", "結末", "状況", "内面葛藤", "具体的行動", "余韻"],
    BeforeValidator(normalize_beat_type)
]

class SceneBeatBlock(BaseModel):
    """シーンを構成する最小単位の行動（ビート）。文字列からの自動変換に対応。"""
    beat_type: BeatType = Field(default="導入", description="ビートの役割")  # デフォルト値でバリデーション失敗を防ぐ

    @model_validator(mode="before")
    @classmethod
    def from_string(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"action_description": data, "beat_type": "展開"}
        return data

    action_description: str = Field(default="描写なし", description="具体的な行動描写。キャラが何をし、何が起きるか")  # 必須→デフォルト値付き
    sensory_keywords: List[str] = Field(default_factory=list, description="描写必須の五感。例：焦げた匂い、冷たい風")
    psychology_keywords: List[str] = Field(default_factory=list, description="描写必須の心理キーワード（2つ以上）")
    target_words: int = Field(default=150, description="このビートの最低目標文字数")

    model_config = MODEL_CONFIG_DEFAULTS

class MasterSceneBlock(BaseModel):
    scene_number:     int       = Field(..., description="シーン番号", validation_alias=AliasChoices("scene_number", "scene_id", "no", "id"))
    action:           str       = Field(default="", description="このシーンで起きる主要な出来事")
    dialogue_point:   str       = Field(default="", description="このシーンで必ず交わされるべき重要な会話の要点")
    dramatic_function: str      = Field(default="")
    emotional_payoff: str       = Field(default="")
    beats:            List[SceneBeatBlock] = Field(
        default_factory=list,
        description="インパクトスコアが高い場合のみ生成される詳細ビート（状況・内面葛藤・具体的行動・余韻）",
    )
    bridge_instruction: str      = Field(default="", description="前シーンからの時間・場所・情緒的な繋がりを自然にするための導入指示。")
    impact_score:      int       = Field(default=50, ge=0, le=100, description="シーンの物語上の重要度。高いほど描写を詳細に（Show）、低いほど簡潔に（Tell）。")
    psychological_layer: str     = Field(default="", description="このシーンでのキャラクターの深層心理、内面的な葛藤、モノローグの指針。")

    @field_validator("beats", mode="before")
    @classmethod
    def ensure_beats_list(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            # 文字列が来た場合は単一のビートとしてラップする
            return [{"action_description": v.strip() or "描写なし", "beat_type": "状況"}]
        if isinstance(v, list):
            # リストの要素が文字列の場合、dictに変換して救済（軽量モデル対策）
            return [
                {"action_description": item, "beat_type": "展開"} if isinstance(item, str) else item
                for item in v
            ]
        return v

class PlotBlueprintPhase1(BaseModel):
    thought_process:      str     = Field(default="")
    title:                str     = Field(default="")
    one_line_summary:     str     = Field(default="")
    detailed_blueprint:   str     = Field(default="")
    tension:              Annotated[int, BeforeValidator(extract_int)] = Field(default=50)
    tension_delta:        Annotated[int, BeforeValidator(extract_int)] = Field(default=0)
    catharsis:            Annotated[int, BeforeValidator(extract_int)] = Field(default=0)
    is_catharsis:         bool    = Field(default=False)
    love_meter:           Annotated[int, BeforeValidator(extract_int)] = Field(default=0)
    catharsis_type:       str     = Field(default="なし")
    next_hook:            Annotated[CliffhangerDef, BeforeValidator(ensure_cliffhanger_obj)] = Field(default_factory=CliffhangerDef)
    misunderstanding_gap: str     = Field(default="")
    current_chain_phase:  Annotated[ChainPhase, BeforeValidator(normalize_chain_phase)] = Field(default="Friction")
    emotional_payoff:     str     = Field(default="")
    resolution_style:     str     = Field(default="Cheat")
    burned_cost_or_loot:  Annotated[str, BeforeValidator(ensure_str)] = Field(default="なし")
    thematic_milestone:   str     = Field(default="なし")
    antagonist_status:    str     = Field(default="現状維持")
    is_plot_twist:        bool    = Field(default=False)
    stress_delta:         int     = Field(default=0, description="0〜100の整数で今話のストレス増減値")
    lite_model_director_notes: str = Field(default="")

class PlotBlueprintPhase1Batch(BaseModel):
    """複数話のPhase 1設計図を一括で保持するモデル"""
    episodes: List[PlotBlueprintPhase1] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS

class PlotBlueprintPhase2(BaseModel):
    scenes:               List[MasterSceneBlock] = Field(default_factory=list)
    script_content:       str     = Field(default="")

class BaseEngine(BaseModel):
    model_config = {
        **MODEL_CONFIG_DEFAULTS,
        "extra": "allow"
    }

    @classmethod
    def get_routing_keys(cls) -> list[str]:
        """このエンジンが引き受けるべきフラットキーのリストを返す"""
        return list(cls.model_fields.keys())

    @model_validator(mode="before")
    @classmethod
    def normalize_engine_data(cls, data: Any) -> Any:
        """
        エンジン固有のデータ正規化フック。
        サブクラスでオーバーライドして、型変換や構造調整を行う。
        """
        return data

class PlotCoreInfo(BaseModel):
    ep_num:               int     = Field(default=0, validation_alias=AliasChoices("ep_num", "episode_num", "episode", "ep", "no", "number"))
    thought_process:      str     = Field(default="", description="プロット作成前の思考")
    title:                str     = Field(default="", description="この話のサブタイトル")
    one_line_summary:     str     = Field(default="", max_length=150, description="この話の核心を突く一行あらすじ")
    detailed_blueprint:   str     = Field(default="", max_length=3000, description="物語の設計図")

class PlotAnalytics(BaseEngine):
    tension:              Annotated[int, BeforeValidator(extract_int)] = Field(default=50, validation_alias=AliasChoices("tension", "intensity"))
    tension_delta:        Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="緊張・摩擦の量", validation_alias=AliasChoices("tension_delta", "stress", "stress_delta"))
    catharsis:            Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="カタルシスの量", validation_alias=AliasChoices("catharsis", "catharsis_delta"))
    is_catharsis:         bool    = Field(default=False, validation_alias=AliasChoices("is_catharsis", "catharsis_flag"))
    love_meter:           Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="好感度の変化量", validation_alias=AliasChoices("love_meter", "love", "affinity"))
    catharsis_type:       str     = Field(default="なし", validation_alias=AliasChoices("catharsis_type", "catharsis_style"))
    emotional_payoff:     str     = Field(default="", validation_alias=AliasChoices("emotional_payoff", "payoff"))
    resolution_style:     str     = Field(default="Cheat", validation_alias=AliasChoices("resolution_style", "style", "resolution"))
    antagonist_status:    str     = Field(default="現状維持", validation_alias=AliasChoices("antagonist_status", "enemy_status", "villain_status"))
    state_integrity_score: int    = Field(default=100)
    emotional_hook:       Optional[EmotionalHookSpec] = Field(default=None, description="この話の感情設計仕様")
    sharp_edges:          List[SharpEdgeSpec] = Field(default_factory=list, description="削ってはいけない角")
    quality_polish_status: Literal["pending", "passed", "rejected_edge_loss"] = Field(default="pending", description="品質磨き上げステータス")

class PlotForeshadowing(BaseEngine):
    """
    汎用的な伏線管理モデル。
    EnigmaAnalytics のベースとして機能し、基本的な情報レイヤーと伏線管理を担う。
    """
    information_layers:   Dict[str, List[str]] = Field(default_factory=dict, description="陣営別（Protagonist, Antagonist, Public）の既知情報", validation_alias=AliasChoices("information_layers", "info_layers"))
    truth_ledger_updates: Dict[str, List[str]] = Field(default_factory=dict, description="【V5.0】今回の話で各キャラクターが新たに知った事実のリスト", validation_alias=AliasChoices("truth_ledger_updates", "truth_updates"))
    knowledge_delta:      float = Field(default=0.0, description="周囲との知識/知能格差のスコア (0.0-1.0)", validation_alias=AliasChoices("knowledge_delta", "intel_gap"))
    foreshadowing_refs:   List[str] = Field(default_factory=list, description="この回で設置/回収された伏線ID", validation_alias=AliasChoices("foreshadowing_refs", "refs"))
    truth_convergence:    float = Field(default=0.0, description="敵対者が真相に辿り着くまでの論理的収束度 (0.0 - 1.0)", validation_alias=AliasChoices("truth_convergence", "convergence"))
    knowledge_friction:   float = Field(default=0.0, description="主人公の策が環境（インフラ、常識）に阻まれる指数 (0.0 - 1.0)", validation_alias=AliasChoices("knowledge_friction", "friction"))
    foreshadowing_ledger: List[Dict[str, Any]] = Field(default_factory=list, description="未回収の伏線リスト", validation_alias=AliasChoices("foreshadowing_ledger", "ledger"))

class RedHerringItem(BaseModel):
    id: int
    clue: str
    ep_num: int
    resolved: bool = False
    resolution: str = ""
    resolve_ep_num: Optional[int] = None

    model_config = MODEL_CONFIG_DEFAULTS

class EnigmaAnalytics(PlotForeshadowing):
    """
    Enigmaエンジン専用の分析モデル。
    PlotForeshadowing を継承し、型変換（extract_float）を適用した定義を上書きする。
    """
    knowledge_delta:      Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="周囲との知識/知能格差のスコア (0.0-1.0)", validation_alias=AliasChoices("knowledge_delta", "intel_gap"))
    truth_convergence:    Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="敵対者が真相に辿り着くまでの論理的収束度 (0.0 - 1.0)", validation_alias=AliasChoices("truth_convergence", "convergence"))
    knowledge_friction:   Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="主人公の策が環境（インフラ、常識）に阻まれる指数 (0.0 - 1.0)", validation_alias=AliasChoices("knowledge_friction", "friction"))

    red_herrings: List[RedHerringItem] = Field(default_factory=list)
    unfairness_score: float = Field(default=0.0)

    def add_red_herring(self, clue: str, ep_num: int) -> int:
        next_id = len(self.red_herrings) + 1
        item = RedHerringItem(id=next_id, clue=clue, ep_num=ep_num)
        self.red_herrings.append(item)
        return next_id

    def eliminate_red_herring(self, rh_id: int, ep_num: int, resolution: str) -> None:
        for rh in self.red_herrings:
            if rh.id == rh_id:
                rh.resolved = True
                rh.resolve_ep_num = ep_num
                rh.resolution = resolution
                break

class ComfortAnalytics(BaseEngine):
    qol_delta:           Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="この話によるQOL向上値")
    veneration_gain:     Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="この話による崇拝度の上昇")
    fulfillment_delta:   Dict[str, float] = Field(default_factory=dict, description="各次元の充足向上")
    is_miracle_occurrence: bool = Field(default=False, description="日常が奇跡として誤認されたか")
    discovery_item:      Optional[str] = Field(default=None, description="この話で新しく発見/発明されたもの")
    sanctuary_event:     Optional[str] = Field(default=None, description="聖域の強化または対比イベントの記述")

    model_config = MODEL_CONFIG_DEFAULTS

class CoreEngineMixin(BaseModel):
    core_info: PlotCoreInfo = Field(default_factory=PlotCoreInfo)
    analytics: PlotAnalytics = Field(default_factory=PlotAnalytics)
    foreshadowing: PlotForeshadowing = Field(default_factory=PlotForeshadowing)

class EnigmaMixin(CoreEngineMixin):
    enigma: EnigmaAnalytics = Field(default_factory=EnigmaAnalytics)

class ComfortMixin(CoreEngineMixin):
    comfort: ComfortAnalytics = Field(default_factory=ComfortAnalytics)

from typing import Generic, TypeVar

T = TypeVar("T", bound=CoreEngineMixin)

class PlotEpisodeBase(FlatModelMixin, CoreEngineMixin, Generic[T]):
    """
    すべてのエピソードが共通で持つ最小構成のベースクラス。
    特定のエンジン (Enigma, Comfort等) は、継承先の特化モデルで Mixin として追加する。
    """
    @classmethod
    def _get_sub_model_names(cls) -> list[str]:
        names = []
        for k, v in cls.model_fields.items():
            ann = v.annotation
            ann_str = str(ann)
            if any(name in ann_str for name in ["PlotCoreInfo", "BaseEngine", "PlotAnalytics", "PlotForeshadowing", "EnigmaAnalytics", "ComfortAnalytics"]):
                names.append(k)
            else:
                try:
                    if isinstance(ann, type) and (issubclass(ann, BaseEngine) or issubclass(ann, PlotCoreInfo)):
                        names.append(k)
                except TypeError:
                    pass
        return names

    @property
    def tension(self) -> int:
        return self.analytics.tension

    @tension.setter
    def tension(self, value: int):
        self.analytics.tension = value

    @property
    def tension_delta(self) -> int:
        return self.analytics.tension_delta

    @tension_delta.setter
    def tension_delta(self, value: int):
        self.analytics.tension_delta = value

    @property
    def catharsis(self) -> int:
        return self.analytics.catharsis

    @catharsis.setter
    def catharsis(self, value: int):
        self.analytics.catharsis = value

    @property
    def is_catharsis(self) -> bool:
        return self.analytics.is_catharsis

    @is_catharsis.setter
    def is_catharsis(self, value: bool):
        self.analytics.is_catharsis = value

    @property
    def love_meter(self) -> int:
        return self.analytics.love_meter

    @love_meter.setter
    def love_meter(self, value: int):
        self.analytics.love_meter = value

    @property
    def catharsis_type(self) -> str:
        return self.analytics.catharsis_type

    @catharsis_type.setter
    def catharsis_type(self, value: str):
        self.analytics.catharsis_type = value

    @property
    def emotional_payoff(self) -> str:
        return self.analytics.emotional_payoff

    @emotional_payoff.setter
    def emotional_payoff(self, value: str):
        self.analytics.emotional_payoff = value

    @property
    def resolution_style(self) -> str:
        return self.analytics.resolution_style

    @resolution_style.setter
    def resolution_style(self, value: str):
        self.analytics.resolution_style = value

    @property
    def antagonist_status(self) -> str:
        return self.analytics.antagonist_status

    @antagonist_status.setter
    def antagonist_status(self, value: str):
        self.analytics.antagonist_status = value

    extra_engines: Dict[str, Any] = Field(default_factory=dict, description="未知・追加エンジンのデータスロット")

    @property
    def detailed_blueprint(self) -> str:
        core_info = self.__dict__.get("core_info")
        return core_info.detailed_blueprint if core_info else ""

    @detailed_blueprint.setter
    def detailed_blueprint(self, value: str):
        core_info = self.__dict__.get("core_info")
        if core_info:
            core_info.detailed_blueprint = value

    @property
    def title(self) -> str:
        core_info = self.__dict__.get("core_info")
        return core_info.title if core_info else ""

    @title.setter
    def title(self, value: str):
        core_info = self.__dict__.get("core_info")
        if core_info:
            core_info.title = value

    @property
    def one_line_summary(self) -> str:
        core_info = self.__dict__.get("core_info")
        return core_info.one_line_summary if core_info else ""

    @one_line_summary.setter
    def one_line_summary(self, value: str):
        core_info = self.__dict__.get("core_info")
        if core_info:
            core_info.one_line_summary = value

    @property
    def thought_process(self) -> str:
        core_info = self.__dict__.get("core_info")
        return core_info.thought_process if core_info else ""

    @thought_process.setter
    def thought_process(self, value: str):
        core_info = self.__dict__.get("core_info")
        if core_info:
            core_info.thought_process = value

    @property
    def ep_num(self) -> int:
        core_info = self.__dict__.get("core_info")
        return core_info.ep_num if core_info else 0

    @ep_num.setter
    def ep_num(self, value: int):
        core_info = self.__dict__.get("core_info")
        if core_info:
            core_info.ep_num = value

    next_hook:            Annotated[CliffhangerDef, BeforeValidator(ensure_cliffhanger_obj)] = Field(default_factory=CliffhangerDef, validation_alias=AliasChoices("next_hook", "cliffhanger", "hook"))
    misunderstanding_gap: str     = Field(default="", validation_alias=AliasChoices("misunderstanding_gap", "gap", "irony"))
    scenes:               List[MasterSceneBlock] = Field(default_factory=list)
    script_content:       str     = Field(default="", validation_alias=AliasChoices("script_content", "script", "manuscript", "content", "final_content"))
    current_chain_phase:  Annotated[ChainPhase, BeforeValidator(normalize_chain_phase)] = Field(default="Friction", validation_alias=AliasChoices("current_chain_phase", "phase", "chain_phase"))
    burned_cost_or_loot:  Annotated[str, BeforeValidator(ensure_str)] = Field(default="なし", validation_alias=AliasChoices("burned_cost_or_loot", "cost", "loot"))
    thematic_milestone:   str     = Field(default="なし", validation_alias=AliasChoices("thematic_milestone", "milestone"))
    healed_fields:        List[str] = Field(default_factory=list)
    is_micro_catharsis:   bool    = Field(default=False, description="摩擦期間中の小規模な解放フラグ")
    information_asymmetry_level: Annotated[float, BeforeValidator(extract_float)] = Field(default=0.0, description="情報の非対称性（読者のみが知る優位性）の強度 0.0-1.0")
    lite_model_director_notes: str = Field(default="", validation_alias=AliasChoices("lite_model_director_notes", "self_critique", "director_notes", "notes"))
    emotional_resonance_score: Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="感情共鳴スコア (1-100)", validation_alias=AliasChoices("emotional_resonance_score", "resonance", "emotional_resonance"))
    thematic_depth_score:      Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="テーマの深さスコア (1-100)", validation_alias=AliasChoices("thematic_depth_score", "depth", "thematic_depth"))
    literary_beauty_score:     Annotated[int, BeforeValidator(extract_int)] = Field(default=0, description="文章の美しさスコア (1-100)", validation_alias=AliasChoices("literary_beauty_score", "beauty", "literary_beauty"))

    @model_validator(mode="before")
    @classmethod
    def unwrap_plot_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Wrapper peeling
            for wrapper in ["metadata", "data", "plot", "episode", "results"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # 動的ルーティング: 各サブモデルの定義フィールド名から自動マッピング
            static_routing_map = {
                "core_info": PlotCoreInfo,
                "analytics": PlotAnalytics,
                "foreshadowing": PlotForeshadowing,
                "enigma": EnigmaAnalytics,
                "comfort": ComfortAnalytics,
            }
            sub_models_names = cls._get_sub_model_names()
            for sub_name in sub_models_names:
                model_cls = static_routing_map.get(sub_name) or cls.model_fields[sub_name].annotation
                if isinstance(model_cls, str) or not isinstance(model_cls, type):
                    continue
                # すでにネストされた構造でデータがある場合はそのまま利用
                if sub_name in data and isinstance(data[sub_name], dict):
                    continue

                if sub_name not in data:
                    if hasattr(model_cls, "get_routing_keys"):
                        routing_keys = model_cls.get_routing_keys()
                    else:
                        routing_keys = list(model_cls.model_fields.keys())
                    extracted_data = {k: data[k] for k in routing_keys if k in data}
                    if extracted_data:
                        data[sub_name] = extracted_data

            # 未定義データの抽出
            all_routed_keys = set()
            for sub_name in sub_models_names:
                if sub_name in data:
                    sub_val = data[sub_name]
                    if isinstance(sub_val, dict):
                        all_routed_keys.update(sub_val.keys())

            # 汎用フィールドを除外して extra_engines へ
            generic_fields = {
                "next_hook", "misunderstanding_gap", "scenes", "script_content",
                "current_chain_phase", "burned_cost_or_loot", "thematic_milestone",
                "healed_fields", "is_micro_catharsis", "information_asymmetry_level",
                "lite_model_director_notes", "emotional_resonance_score",
                "thematic_depth_score", "literary_beauty_score"
            }

            remaining_keys = [k for k in data.keys() if k not in all_routed_keys and k not in generic_fields and k not in sub_models_names]
            if remaining_keys:
                extra = {}
                for k in remaining_keys:
                    extra[k] = data.pop(k)
                data["extra_engines"] = {**data.get("extra_engines", {}), **extra}

        return data

    @model_serializer(mode="wrap")
    def serialize_flat(self, handler) -> Dict[str, Any]:
        dumped = handler(self)
        for sub_model in self.__class__._get_sub_model_names():
            if sub_model in dumped and isinstance(dumped[sub_model], dict):
                data = dumped.pop(sub_model)
                dumped.update(data)

        if "extra_engines" in dumped and isinstance(dumped["extra_engines"], dict):
            extra = dumped.pop("extra_engines")
            dumped.update(extra)

        return dumped

    def __getattr__(self, item: str) -> Any:
        # Fallbacks for dynamic access and backwards compatibility
        if item in ("detailed_blueprint", "title", "one_line_summary", "thought_process", "ep_num"):
            core_info = self.__dict__.get("core_info")
            if core_info and hasattr(core_info, item):
                return getattr(core_info, item)

        if item == "self_critique": return self.lite_model_director_notes
        if item == "stress": return self.analytics.tension_delta

        for sub_model in self.__class__._get_sub_model_names():
            try:
                model_instance = object.__getattribute__(self, sub_model)
                if hasattr(model_instance, item):
                    return getattr(model_instance, item)
            except AttributeError:
                pass

        try:
            extra_engines = object.__getattribute__(self, "extra_engines")
            if item in extra_engines:
                return extra_engines[item]
        except AttributeError:
            pass

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def get(self, key: str, default=None):
        """
        辞書ライクなアクセスを提供する互換性用メソッド。
        """
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def to_catharsis_summary(self) -> dict:
        """カタルシス関連データを要約して返す"""
        return {
            "ep_num": self.ep_num,
            "is_catharsis": self.is_catharsis,
            "catharsis": self.catharsis,
            "catharsis_type": self.catharsis_type,
            "tension": self.tension,
            "tension_delta": self.tension_delta,
            "cumulative_stress": getattr(self.analytics, "cumulative_stress", self.tension_delta),
        }

    model_config = {
        **MODEL_CONFIG_DEFAULTS,
        "extra": "allow"
    }

class PlotEpisode(PlotEpisodeBase[CoreEngineMixin], EnigmaMixin, ComfortMixin):
    """
    デフォルトの PlotEpisode モデル。
    現在は互換性のためにすべてのエンジン Mixin を含んでいるが、
    将来的にジャンル別特化モデルへ移行する。
    """
    candidates: List[PlotEpisodeBase] = Field(default_factory=list, description="AIが提示した複数の候補案")
    @model_validator(mode="before")
    @classmethod
    def unwrap_plot_metadata(cls, data: Any) -> Any:
        # Base クラスの正規化ロジックに委譲 (FlatModelMixin + extra_engines 処理)
        return super().unwrap_plot_metadata(data)

def plot_episode_factory(genre: str, **data) -> PlotEpisode:
    """
    ジャンルに応じて適切な特化モデルを生成するファクトリ関数。
    """
    genre_map = {
        "mystery": MysteryEpisode,
        "slice_of_life": SliceOfLifeEpisode,
        "drama": DramaEpisode,
    }
    model_cls = genre_map.get(genre.lower(), PlotEpisode)
    return model_cls(**data)

class MysteryEpisode(PlotEpisodeBase, EnigmaMixin):
    """
    ミステリー・サスペンス特化モデル。
    Enigma Analytics (伏線・真相管理) を優先的に保持。
    """
    def calculate_mystery_catharsis(self) -> int:
        base_score = int((self.enigma.knowledge_delta * self.enigma.truth_convergence) * 100)
        resolved_count = sum(1 for rh in self.enigma.red_herrings if rh.resolved)
        bonus = resolved_count * 10
        return base_score + bonus

class SliceOfLifeEpisode(PlotEpisodeBase[ComfortMixin], ComfortMixin):
    """
    日常・癒やし特化モデル。
    Comfort Analytics (QOL・充足感管理) を優先的に保持。
    """

from typing import Union


class DramaEpisode(PlotEpisodeBase[Union[EnigmaMixin, ComfortMixin]], EnigmaMixin, ComfortMixin):
    """
    人間ドラマ特化モデル。
    謎解きと感情的充足の両面を保持。
    """
    pass

class RoadmapItem(FlatModelMixin, BaseModel):
    ep_num:              int     = Field(..., description="話数", validation_alias=AliasChoices("ep_num", "episode_num", "episode", "ep", "no", "number"))
    one_line_summary:    str     = Field(..., description="不可逆に前進する1行あらすじ", validation_alias=AliasChoices("one_line_summary", "one_line", "summary", "outline"))
    resolution_style:    Literal["Cheat", "Logic", "Focus_Drama"] = Field(..., validation_alias=AliasChoices("resolution_style", "style", "resolution"))
    burned_cost_or_loot: str     = Field(default="なし", validation_alias=AliasChoices("burned_cost_or_loot", "cost", "loot"))
    thematic_milestone:  str     = Field(default="なし")
    antagonist_status:   str     = Field(..., validation_alias=AliasChoices("antagonist_status", "enemy_status", "villain_status"))
    is_catharsis:        bool    = Field(default=False)
    foreshadowing_setup:  str     = Field(default="なし", description="この話で設置される伏線の内容")
    foreshadowing_payoff: str     = Field(default="なし", description="この話で回収される伏線の内容")

    @model_validator(mode="before")
    @classmethod
    def validate_roadmap_item(cls, data: Any) -> Any:
        data = cls.unwrap_flat_metadata(data)

        if isinstance(data, dict):
            # Resolution Style Normalization (Keeping the specific logic from original)
            res_style = data.get("resolution_style") or data.get("style") or data.get("resolution")
            if res_style:
                style_lower = str(res_style).lower()
                if any(x in style_lower for x in ["logic", "知", "頭脳", "戦略", "策", "頭", "謎", "分析", "推理", "思考", "買収", "経済", "物流", "株主"]):
                    data["resolution_style"] = "Logic"
                elif any(x in style_lower for x in ["drama", "ドラマ", "感情", "絆", "友情", "救", "対話", "心", "愛", "結束"]):
                    data["resolution_style"] = "Focus_Drama"
                else:
                    data["resolution_style"] = "Cheat"

        return data

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    model_config = MODEL_CONFIG_DEFAULTS

class RoadmapList(BaseModel):
    full_story_roadmap: List[RoadmapItem] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS

class ArcBlueprint(BaseModel):
    arc_num:  int = Field(..., validation_alias=AliasChoices("arc_num", "arc_number", "number", "no"))
    start_ep: int = Field(..., validation_alias=AliasChoices("start_ep", "start_episode", "start"))
    end_ep:   int = Field(..., validation_alias=AliasChoices("end_ep", "end_episode", "end"))
    title:    str = Field(default="無題")
    summary:  str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def resolve_arc_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # Field mapping
            for target, aliases in {
                "arc_num": ["arc_num", "arc_number", "number", "no"],
                "start_ep": ["start_ep", "start_episode", "start"],
                "end_ep": ["end_ep", "end_episode", "end"],
                "title": ["title"],
                "summary": ["summary", "description"]
            }.items():
                for alias in aliases:
                    if alias in data and data[alias] is not None:
                        try:
                            if target in ["arc_num", "start_ep", "end_ep"]:
                                data[target] = int(extract_int(data[alias]) if hasattr(extract_int, '__call__') else data[alias])
                            else:
                                data[target] = data[alias]
                        except Exception:
                            try:
                                data[target] = int(data[alias])
                            except Exception:
                                pass
                        break

            # Check defaults for required fields
            if "arc_num" not in data or data["arc_num"] is None:
                data["arc_num"] = 1
            if "start_ep" not in data or data["start_ep"] is None:
                data["start_ep"] = 1
            if "end_ep" not in data or data["end_ep"] is None:
                data["end_ep"] = data.get("start_ep", 1)
        return data

    model_config = MODEL_CONFIG_DEFAULTS

    # Provide a dict-like interface for compatibility with code that
    # expects a mapping.
    def get(self, key: str, default=None):
        if key in self.model_fields:
            return getattr(self, key)
        return default


class ArcList(BaseModel):
    """アークリスト（章構成）の一括生成・検証用モデル"""
    arcs: List[ArcBlueprint] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_arc_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "arcs", "arc_list"]:
                if wrapper in data and isinstance(data[wrapper], list) and len(data) == 1:
                    data = {"arcs": data[wrapper]}
                    break
                elif wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class UltraFastPlotBatch(BaseModel):
    """超高速・統合生成用のPydanticモデル。複数エピソードの詳細プロット設計図を一括バッチ生成する。"""
    plots: List[PlotEpisode] = Field(..., description="指定された初期話数分の詳細プロット設計図のリスト（通常は第1〜3話）")

    model_config = MODEL_CONFIG_DEFAULTS

class PlotDetail(PlotEpisode):
    """
    プロットの詳細展開結果を保持するモデル。
    PlotEpisode を継承し、さらに詳細な分析や執筆指示を含む。
    """
    detailed_analysis: str = Field(default="", description="展開後の詳細な物語分析")
    writing_instructions: str = Field(default="", description="執筆時の具体的な指示・留意点")

    model_config = MODEL_CONFIG_DEFAULTS


class CatharsisPattern(BaseModel):
    """ストレス蓄積とカタルシス解放の波パターンを定義するモデル"""
    cumulative_stress: int = Field(default=0, description="現在の累積ストレス値")
    catharsis_points: List[int] = Field(default_factory=list, description="カタルシス発生話数のリスト")
    tension_wave: List[int] = Field(default_factory=list, description="各話のtension値の履歴")
    pattern_type: str = Field(default="wave", description="波パターン種類: gradual/spike/wave/explosion")
    small_catharsis_ratio: float = Field(default=0.7, description="小カタルシスの比率")
    medium_catharsis_ratio: float = Field(default=0.15, description="中カタルシスの比率")
    large_catharsis_ratio: float = Field(default=0.15, description="大カタルシスの比率")

    model_config = MODEL_CONFIG_DEFAULTS

    def to_summary(self) -> dict:
        return {
            "cumulative_stress": self.cumulative_stress,
            "catharsis_count": len(self.catharsis_points),
            "catharsis_positions": self.catharsis_points,
            "pattern_type": self.pattern_type,
            "tension_wave": self.tension_wave,
        }
