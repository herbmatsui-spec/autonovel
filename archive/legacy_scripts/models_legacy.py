"""
models.py - データモデル定義モジュール
全ての Pydantic モデル（DB モデル含む）を集約。
型の一元管理により、追加・変更が容易。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

# ==========================================
# Type Definitions / Enums
# ==========================================
ChainPhase = Literal["Hate", "Prep", "Payoff"]
StyleKey = Literal["style_web_standard", "style_serious_fantasy", "style_psychological_loop",
                   "style_chat_log", "style_villainess_elegant", "style_military_rational",
                   "style_comedy_speed", "style_dark_hero", "style_overlord", "style_bookworm_daily", "style_light_fun"]

# Pydantic V2 internal configuration to prevent naming conflicts and allow 'model_' prefixes
MODEL_CONFIG_DEFAULTS = {
    "populate_by_name": True,
    "extra": "allow",
    "protected_namespaces": ()
}


# ==========================================
# 例外クラス
# ==========================================
class EngineError(Exception):
    """API生成に関連する基底例外"""
    pass

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
# キャラクター関連モデル
# ==========================================
class CharacterRelationship(BaseModel):
    target_char_name: str = Field(..., description="関係性を持つ相手のキャラクター名")
    type: str = Field(..., description="関係性の種類（例: ライバル, 師弟, 依存, 秘密の恋人, 恩人, 宿敵）")
    description: str = Field(default="", description="関係性の具体的な内容や背景")
    intensity: int = Field(default=3, ge=1, le=5, description="関係性の強度（1:弱い〜5:強い）")
    secret_aspect: Optional[str] = Field(default=None, description="関係性の秘密の側面や裏の顔")

    model_config = MODEL_CONFIG_DEFAULTS

class CharacterRegistry(BaseModel):
    name:                str             = Field(default="")
    role:                str             = Field(default="")
    gender:              str             = Field(default="")
    age:                 str             = Field(default="")
    appearance:          str             = Field(default="")
    personality:         str             = Field(default="", alias="traits")
    surface_persona:     str             = Field(default="", description="周囲からどう見られているか、演じている役割")
    inner_conflict:      str             = Field(default="", description="演じている自分と本当の望みの間の葛藤")
    core_trauma:         str             = Field(default="", description="過去のトラウマや原初の欠落")
    save_the_cat_event:  str             = Field(default="", description="読者が共感する人間味ある善行")
    first_person:        str             = Field(default="私", description="一人称（私、俺、僕、わらわ等）")
    second_person:       str             = Field(default="貴方", description="二人称（貴方、お前、君、貴様等）")
    suffix_style:        str             = Field(default="", description="特徴的な語尾（〜ですわ、〜だぜ、〜なのだ等）")
    ability:             str             = Field(default="", alias="power")
    background:          str             = Field(default="", alias="bg")
    tone:                str             = Field(default="")
    iron_constraint:     str             = Field(default="", description="絶対に破らない行動原則・禁忌", alias="iron_const")
    fate_link:           str             = Field(default="", description="世界の因果律との繋がり、世界が壊れた際に失うもの")
    social_mask_vs_truth: str            = Field(default="", description="表向きの社会的仮面と、夜一人でいる時に見せる剥き出しの真実の対比")
    pronouns:            Dict[str, str]  = Field(default_factory=dict)
    relationships:       List[CharacterRelationship] = Field(default_factory=list, alias="relations")
    dialogue_samples:    List[str]       = Field(default_factory=list, alias="dlg_smp")
    keywords:            List[str]       = Field(default_factory=list, alias="kws")
    expansion_hooks:     List[str]       = Field(default_factory=list, alias="exp_hooks", description="描写を膨らませるための固有要素")

    model_config = MODEL_CONFIG_DEFAULTS

    def to_prompt(self) -> str:
        """シンプルなプロンプト文字列を生成する"""
        return (
            f"- Name: {self.name} ({self.role})\n"
            f"- Personality: {self.personality}\n"
            f"- Ability: {self.ability}\n"
            f"- Tone: {self.tone}\n"
            f"- IronConst: {self.iron_constraint}\n"
            f"- Pronouns: I={self.first_person}, You={self.second_person}\n"
            f"- Suffix: {self.suffix_style}\n"
            f"- ExpHooks: {', '.join(self.expansion_hooks)}\n"
        )

    def get_context_prompt(self, current_state: str = "") -> str:
        """AIへの投入用に全フィールドを展開した詳細プロンプト文字列を生成する"""
        import json as _json
        prompt = f"■ {self.name} ({self.role})"
        if current_state:
            prompt += f" [CURRENT STATE: {current_state}]"
        prompt += "\n"
        prompt += f"- Tone: {self.tone}\n"
        prompt += f"- Personality: {self.personality}\n"
        prompt += f"- Ability: {self.ability}\n"
        prompt += f"- IronConst: {self.iron_constraint}\n"
        prompt += f"- Background: {self.background}\n"
        prompt += f"- ExpansionHooks: {', '.join(self.expansion_hooks)}\n"
        rels_str = _json.dumps(
            {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in getattr(self, "relationships", {}).items()},
            ensure_ascii=False,
        )
        prompt += f"- Rels: {rels_str}\n"
        prompt += f"- DlgSmp: {_json.dumps(self.dialogue_samples, ensure_ascii=False)}\n"
        return prompt

    @classmethod
    def from_db(cls, data: Union[dict, str]) -> CharacterRegistry:
        """DBからの復元時に型変換を安全に行う"""
        import json
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}
        return cls.model_validate(data) if isinstance(data, dict) else cls()


# ==========================================
# 世界観・伏線モデル
# ==========================================
class NarrativeConstraint(BaseModel):
    """物語上の絶対遵守すべき論理制約（因果律ユニットテスト用）"""
    subject: str = Field(..., description="対象（キャラ名、アイテム名）")
    constraint: str = Field(..., description="制約内容（〜を知らない、〜を持っている、〜できない等）")
    importance: Literal["Low", "Medium", "High"] = Field(default="High")

    model_config = MODEL_CONFIG_DEFAULTS

class Foreshadowing(BaseModel):
    setup_ep:    str = Field(default="", description="伏線を張る話数。未定なら'TBD'。例: '第3話'")
    payoff_ep:   str = Field(default="", description="伏線を回収する目標話数。例: '第15話'")
    description: str = Field(default="", description="伏線の具体的な内容（例：主人公が拾った錆びた鍵が実は王家の証である等、具体的に）")
    exposure_level: int = Field(default=3, ge=1, le=5, description="読者へのバレやすさ(1:完全隠蔽〜5:露骨な予告)")
    is_red_herring: bool = Field(default=False, description="ミスリード（偽の伏線）かどうか")
    true_meaning: str = Field(default="", description="ミスリードの場合の、真の伏線・真相")


class ClimaxScene(BaseModel):
    timing:               str = Field(default="", description="発生予定の話数やタイミング。例: '第10話 決戦時'")
    event:                str = Field(default="", description="名場面の内容。何が起き、誰がどうなり、どのようなカタルシスがあるか")
    target_emotion:       str = Field(default="", description="読者に抱かせたい感情（例：絶望、鳥肌が立つような爽快感、感動の涙）")
    pre_written_dialogue: str = Field(default="", description="決定的なセリフの応酬（魂の対話）")


class WorldRules(BaseModel):
    magic_cost_and_taboo:          str             = Field(default="なし", description="魔法やスキルの残酷な代償と世界の禁忌")
    social_hierarchy_and_discrimination: str       = Field(default="なし", description="主人公が迫害される絶対的な社会的構造")
    hidden_truths:                 Dict[str, str]  = Field(default_factory=dict, description="絶望的な真実・最大の伏線を3つ以上")
    geopolitics_and_economy:       str             = Field(default="なし", description="資源の偏り、通貨の価値、地政学的緊張")
    religious_dogma_and_heresy:    str             = Field(default="なし", description="信仰と、それを破った際の社会的制裁")
    causality_map:                 List[str]       = Field(default_factory=list, description="設定間の不可避な因果律の連鎖（AがBを生み、Cに繋がる等）")
    foreshadowing_map:             List[Foreshadowing] = Field(default_factory=list)
    active_constraints:            List[NarrativeConstraint] = Field(default_factory=list, description="現在有効な論理制約リスト")
    climax_scenes:                 List[ClimaxScene]   = Field(default_factory=list, description="読者の心を揺さぶる名場面(3〜5個)")
    mystery_disclosure_schedule:   List[Dict[str, Any]] = Field(default_factory=list)

# ==========================================
# アンカー（設定固定）モデル
# ==========================================
class AnchorResponse(BaseModel):
    anchor_id: str = Field(default="", description="アンカーID")
    content: str = Field(default="", description="確定した事実や設定の内容")
    category: str = Field(default="General", description="カテゴリ")
    importance: int = Field(default=3, ge=1, le=5)

    model_config = MODEL_CONFIG_DEFAULTS

# ==========================================
# マーケティング・プロット補助モデル
# ==========================================
class MarketingAssets(BaseModel):
    catchcopies:       List[str]            = Field(default_factory=list)
    tags:              List[str]            = Field(default_factory=list)
    ab_test_candidates: List[Dict[str, Any]] = Field(default_factory=list, description="タイトル・タグのABテスト案")


class ReviewLog(BaseModel):
    plan_name:             str = Field(default="")
    experiment_1_score:    int = Field(default=0)
    experiment_1_comments: str = Field(default="")
    experiment_2_score:    int = Field(default=0)
    experiment_2_comments: str = Field(default="")


class DynamicPacing(BaseModel):
    ep_range:        str = Field(default="")
    phase_name:      str = Field(default="")
    required_events: str = Field(default="")


class StoryThread(BaseModel):
    id:                    str     = Field(..., description="スレッドID")
    description:           str     = Field(..., description="内容")
    status:                Literal["Active", "Dormant", "Resolving", "Closed"] = Field(default="Active")
    urgency:               int     = Field(default=1, ge=1, le=5)
    setup_episode:         int     = Field(..., description="発生話数")
    target_resolve_episode: Optional[int] = Field(default=None)
    fermentation_period:   int     = Field(default=5, description="伏線が発酵（潜伏）する期間（話数）")


class WorldState(BaseModel):
    new_facts:             List[str]         = Field(default_factory=list)
    revealed_mysteries:    List[str]         = Field(default_factory=list)
    pending_foreshadowing: List[str]         = Field(default_factory=list)
    story_threads:         List[StoryThread] = Field(default_factory=list)
    dynamic_anchors:       List[str]         = Field(default_factory=list)
    subplot_progression:   Dict[str, int]    = Field(default_factory=dict)
    cumulative_summary:    str               = Field(default="", description="第1話から最新話までの圧縮あらすじ（800文字以内）")
    dependency_graph:      Dict[str, Any]    = Field(default_factory=dict)
    character_states:      Dict[str, str]    = Field(default_factory=dict)


# ==========================================
# プロット・エピソードモデル
# ==========================================
class CliffhangerDef(BaseModel):
    type:        str = Field(default="", description="New Crisis / Shocking Truth / Quiet Foreshadowing")
    description: str = Field(default="")

# AIが吐きがちな表現をLiteralにマッピングするヘルパー
def normalize_beat_type(v: Any) -> str:
    mapping = {
        "Introduction": "導入", "Start": "導入", "In Medias Res": "導入",
        "Development": "展開", "Rising": "展開", "Conclusion": "結末", "End": "結末",
        "Context": "状況", "Background": "状況", "Internal": "内面葛藤", "Thought": "内面葛藤",
        "Action": "具体的行動", "Battle": "具体的行動", "Aftermath": "余韻", "Reflection": "余韻"
    }
    if isinstance(v, str) and v in mapping:
        return mapping[v]
    return v

BeatType = Annotated[
    Literal["導入", "展開", "結末", "状況", "内面葛藤", "具体的行動", "余韻"],
    BeforeValidator(normalize_beat_type)
]

class SceneBeatBlock(BaseModel):
    """シーンを構成する最小単位の行動（ビート）"""
    beat_type: BeatType = Field(..., description="ビートの役割")
    action_description: str = Field(..., description="具体的な行動描写。キャラが何をし、何が起きるか")
    sensory_keywords: List[str] = Field(default_factory=list, description="描写必須の五感。例：焦げた匂い、冷たい風")
    psychology_keywords: List[str] = Field(default_factory=list, description="描写必須の心理キーワード（2つ以上）")
    target_words: int = Field(default=150, description="このビートの最低目標文字数")


class MasterSceneBlock(BaseModel):
    scene_number:     int       = Field(..., description="シーン番号")
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


class PlotEpisode(BaseModel):
    ep_num:               int     = Field(default=0)
    thought_process:      str     = Field(default="", description="プロット作成前の思考。Step A(矛盾検証), Step B(反証論破), Step C(最終結論)の形式で論理的に記述")
    title:                str     = Field(default="", description="この話のサブタイトル")
    one_line_summary:     str     = Field(default="", description="この話の核心を突く一行あらすじ（読者の興味を惹くもの）")
    detailed_blueprint:   str     = Field(default="", description="物語の設計図。起承転結の流れ、状況の変化、キャラの行動を詳細に記述", validation_alias=AliasChoices("detailed_blueprint", "blueprint", "plot", "summary"))
    tension:              int     = Field(default=50)
    stress:               int     = Field(default=0, description="この話を通じて蓄積されるストレスの量（負の値も可）")
    catharsis:            int     = Field(default=0, description="この話で解放されるカタルシスの量")
    is_catharsis:         bool    = Field(default=False)
    love_meter:           int     = Field(default=0, description="この話での好感度の変化量")
    catharsis_type:       str     = Field(default="なし")
    next_hook:            CliffhangerDef = Field(default_factory=CliffhangerDef)
    misunderstanding_gap: str     = Field(default="")
    scenes:               List[MasterSceneBlock] = Field(default_factory=list)
    script_content:       str     = Field(default="", validation_alias=AliasChoices("script_content", "script", "manuscript", "content"))
    current_chain_phase:  ChainPhase = Field(default="Hate")
    emotional_payoff:     str     = Field(default="")
    resolution_style:     str     = Field(default="Cheat") # Literal制約を緩和しsanitizerで補正
    is_plot_twist:        bool    = Field(default=False, description="大どんでん返し回かどうか")
    burned_cost_or_loot:  str     = Field(default="なし")
    thematic_milestone:   str     = Field(default="なし")
    antagonist_status:    str     = Field(default="現状維持")
    lite_model_director_notes: str = Field(default="", description="生成したプロットの弱点と修正点", validation_alias=AliasChoices("lite_model_director_notes", "self_critique", "director_notes"))

    def get(self, key: str, default=None):
        """
        辞書ライクなアクセスを提供する互換性用メソッド。
        エイリアス名の解決も試みる。
        """
        try:
            # 特殊なエイリアス対応
            if key == "self_critique": return self.lite_model_director_notes
            return self.__dict__.get(key, getattr(self, key, default))
        except (AttributeError, KeyError):
            return default

    model_config = MODEL_CONFIG_DEFAULTS


class RoadmapItem(BaseModel):
    ep_num:              int     = Field(..., description="話数")
    one_line_summary:    str     = Field(..., description="不可逆に前進する1行あらすじ")
    resolution_style:    Literal["Cheat", "Logic", "Focus_Drama", "Self_Destruction", "Third_Party", "Misunderstanding_Peace"] = Field(...)
    burned_cost_or_loot: str     = Field(...)
    thematic_milestone:  str     = Field(default="なし")
    antagonist_status:   str     = Field(...)
    is_plot_twist:       bool    = Field(default=False, description="大どんでん返し回かどうか")


class RoadmapList(BaseModel):
    full_story_roadmap: List[RoadmapItem] = Field(default_factory=list)


class ArcBlueprint(BaseModel):
    arc_num:  int = Field(...)
    start_ep: int = Field(...)
    end_ep:   int = Field(...)
    title:    str = Field(default="無題")
    summary:  str = Field(default="")

    model_config = MODEL_CONFIG_DEFAULTS

    # Provide a dict-like interface for compatibility with code that
    # expects a mapping.  The original implementation used `get` to
    # access fields, which is not available on Pydantic models.
    def get(self, key: str, default=None):
        """Return the attribute value or *default* if the key is missing.

        This mirrors the behaviour of ``dict.get`` and allows legacy
        code that treats ``ArcBlueprint`` as a mapping to continue
        functioning without modification.
        """
        # Pydanticの内部管理辞書を直接参照し、無ければ標準の属性取得を試みる
        try:
            return self.__dict__.get(key, getattr(self, key, default))
        except (AttributeError, KeyError):
            return default

class SubplotThread(BaseModel):
    id:             str            = Field(..., description="サブプロットID")
    character_name: str            = Field(..., description="対象キャラクター名（敵やサブキャラ等）")
    objective:      str            = Field(..., description="目的・行動計画")
    current_state:  str            = Field(default="", description="現在の状態・進行状況")
    episodes:       Dict[int, str] = Field(default_factory=dict, description="各話ごとの行動ログ/予定")
    stress:         int            = Field(default=0, description="サブプロット側の蓄積ストレス/緊迫度")
    is_active:      bool           = Field(default=True, description="現在進行中かどうか")

    model_config = MODEL_CONFIG_DEFAULTS

# ==========================================
# 作品全体の設定Bible
# ==========================================
class WorldBibleCore(BaseModel):
    thought_process:     str             = Field(default="", description="企画全体の整合性チェック思考プロセス")
    genre:               str             = Field(default="ファンタジー")
    style_key:           StyleKey        = Field(default="style_web_standard")
    keywords:            str             = Field(default="")
    title:               str             = Field(default="無題")
    concept:             str             = Field(default="")
    target_persona:      str             = Field(default="")
    reader_promise:      str             = Field(default="")
    synopsis:            str             = Field(default="")
    world_settings:      WorldRules      = Field(default_factory=WorldRules)
    mc_profile:          CharacterRegistry = Field(default_factory=CharacterRegistry)
    sub_characters:      List[CharacterRegistry] = Field(default_factory=list)
    marketing_assets:    MarketingAssets = Field(default_factory=MarketingAssets)
    arcs:                List[ArcBlueprint] = Field(default_factory=list)
    review_logs:         List[ReviewLog] = Field(default_factory=list)
    dynamic_pacing_graph: List[DynamicPacing] = Field(default_factory=list)
    villain_parallel_timeline: List[str] = Field(default_factory=list)
    subplots:            List[SubplotThread] = Field(default_factory=list, description="独立したサブプロット管理")
    story_direction:     str             = Field(default="")


class WorldBible(BaseModel):
    id:                  Optional[int]   = Field(default=None)
    genre:               str             = Field(default="ファンタジー")
    style_key:           StyleKey        = Field(default="style_web_standard")
    keywords:            str             = Field(default="")
    title:               str             = Field(default="無題")
    concept:             str             = Field(default="")
    synopsis:            str             = Field(default="")
    world_settings:      WorldRules      = Field(default_factory=WorldRules)
    mc_profile:          CharacterRegistry = Field(default_factory=CharacterRegistry)
    sub_characters:      List[CharacterRegistry] = Field(default_factory=list)
    marketing_assets:    MarketingAssets = Field(default_factory=MarketingAssets)
    anchors:             List[AnchorResponse] = Field(default_factory=list)
    arcs:                List[ArcBlueprint] = Field(default_factory=list)
    plots:               List[PlotEpisode] = Field(default_factory=list)
    thought_process:     str             = Field(default="")
    review_logs:         List[ReviewLog] = Field(default_factory=list)
    dynamic_pacing_graph: List[DynamicPacing] = Field(default_factory=list)
    villain_parallel_timeline: List[str] = Field(default_factory=list)
    subplots:            List[SubplotThread] = Field(default_factory=list, description="独立したサブプロット管理")
    story_direction:     str             = Field(default="")
    full_story_roadmap:  List[RoadmapItem] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS


# ==========================================
# 執筆・分析用モデル
# ==========================================
class EpisodeDraft(BaseModel):
    ep_num:                  int             = Field(default=0)
    anti_pattern_prediction: str             = Field(default="")
    initial_manuscript:      str             = Field(default="")
    entertainment_audit:     str             = Field(default="")
    audit_checklist:         Dict[str, bool] = Field(default_factory=dict)
    final_content:           str             = Field(default="")
    self_critique:           str             = Field(default="")
    summary:                 str             = Field(default="")
    stress_delta:            int             = Field(default=0)
    love_delta:              int             = Field(default=0)
    next_world_state:        WorldState      = Field(default_factory=WorldState)
    cost_consumed:           int             = Field(default=0)


class EpisodeFinalDraft(BaseModel):
    ep_num:          int        = Field(...)
    final_content:   str        = Field(..., description="コンテと台本を統合した決定稿")
    summary:         str        = Field(default="")
    stress_delta:    int        = Field(default=0)
    love_delta:      int        = Field(default=0)
    next_world_state: WorldState = Field(default_factory=WorldState)


class StyleDNA(BaseModel):
    name:        str = Field(default="")
    instruction: str = Field(default="")


class StyleFragment(BaseModel):
    """RAG用：覇権作品の文体断片データ"""
    id: Optional[int] = None
    tag: str = Field(..., description="シーン属性（戦闘、心理、ざまぁ、濡れ場等）")
    content: str = Field(..., description="理想的な文章の断片（100-500文字）")
    embedding_json: Optional[str] = Field(default=None, description="ベクトルデータ（JSON）")
    origin: str = Field(default="Masterpiece", description="出典元")

    model_config = MODEL_CONFIG_DEFAULTS

class MarketingPack(BaseModel):
    catchphrase:    str       = Field(default="")
    kakuyomu_notes: str       = Field(default="")
    tags:           List[str] = Field(default_factory=list)


# ==========================================
# DBモデル（SQLiteの行をPydanticで型付け）
# ==========================================
class BookDbModel(BaseModel):
    id:               int
    title:            str
    genre:            Optional[str]              = None
    concept:          Optional[str]              = None
    synopsis:         Optional[str]              = None
    catchcopy:        Optional[str]              = None
    target_eps:       Optional[int]              = None
    style_dna:        Optional[Union[dict, str]] = None
    status:           Optional[str]              = None
    created_at:       Optional[str]              = None
    marketing_data:   Optional[Union[dict, str]] = None
    cumulative_tension: Optional[int]             = 0


class BranchDbModel(BaseModel):
    id:           int
    book_id:      int
    name:         str
    parent_id:    Optional[int] = None
    fork_ep_num:  Optional[int] = 0
    created_at:   Optional[str] = None


class BibleDbModel(BaseModel):
    id:           int
    book_id:      int
    settings:     Optional[Union[dict, str]] = None
    revealed:     Optional[str]              = None
    version:      Optional[int]              = None
    last_updated: Optional[str]              = None


class PlotDbModel(BaseModel):
    book_id:                   int
    ep_num:                    int
    thought_process:           Optional[str]              = ""
    title:                     Optional[str]              = None
    summary:                   Optional[str]              = None
    detailed_blueprint:        Optional[str]              = None
    tension:                   Optional[int]              = 50
    stress:                    Optional[int]              = 0
    catharsis:                 Optional[int]              = 0
    status:                    Optional[str]              = None
    scenes:                    Optional[List[Dict[str, Any]]] = None
    is_catharsis:              Optional[bool]             = False
    catharsis_type:            Optional[str]              = None
    love_meter:                Optional[int]              = 0
    next_hook:                 Optional[Dict[str, Any]]   = None
    misunderstanding_gap:      Optional[str]              = None
    lite_model_director_notes: Optional[str]              = None
    script_content:            Optional[str]              = None
    current_chain_phase:       Optional[ChainPhase]       = "Hate"
    resolution_style:          Optional[str]              = "Cheat"
    is_plot_twist:             Optional[bool]             = False
    burned_cost_or_loot:       Optional[str]              = "なし"
    antagonist_status:         Optional[str]              = "現状維持"
    thematic_milestone:        Optional[str]              = "なし"

    @field_validator("next_hook", "scenes", mode="before")
    @classmethod
    def ensure_structured_data(cls, v: Any, info: ValidationInfo) -> Any:
        """DBから読み込む際の文字列化されたJSONをパースし、構造化データとして保持する。"""
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                # 文字列をパースできない場合、期待される構造にラップして救済する
                if info.field_name == "scenes":
                    return [{"action": v}]
                elif info.field_name == "next_hook":
                    return {"description": v}
                return v
        return v

    # Compatibility shim for legacy code expecting dict-like access
    def get(self, key: str, default=None):
        try:
            return self.__dict__.get(key, getattr(self, key, default))
        except (AttributeError, KeyError):
            return default

class ChapterDbModel(BaseModel):
    book_id:           int
    ep_num:            int
    title:             Optional[str]              = None
    content:           Optional[str]              = None
    score_story:       Optional[int]              = None
    killer_phrase:     Optional[str]              = None
    summary:           Optional[str]              = None
    world_state:       Optional[Union[dict, str]] = None
    trinity_review_log: Optional[Union[dict, str]] = None
    ai_insight:        Optional[str]              = None
    created_at:        Optional[str]              = None

    @field_validator("world_state", "trinity_review_log", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> Any:
        """DBから読み込む際の文字列化されたJSONをパースし、辞書として保持する。"""
        if isinstance(v, str) and v.strip():
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {"raw_data": parsed}
            except (json.JSONDecodeError, TypeError):
                return {"raw_info": v}
        if v is None:
            return {}
        return v

class CharacterDbModel(BaseModel):
    id:            int
    book_id:       int
    name:          Optional[str]              = None
    role:          Optional[str]              = None
    registry_data: Optional[Union[dict, str]] = None


# ==========================================
# AIプロデューサー診断モデル
# ==========================================
class HegemonyAuditResult(BaseModel):
    refined_keywords:    str       = Field(..., description="提案された覇権キーワード")
    refined_concept:     str       = Field(..., description="ブラッシュアップされたコンセプト")
    refined_mc_suggestion: str     = Field(..., description="読者に刺さる主人公像の提案")
    recommended_tropes:  List[str] = Field(default_factory=list, description="推奨トロープのリスト")


class LogicalAuditResult(BaseModel):
    is_consistent:    bool                    = Field(default=True, description="過去の事実と矛盾がないか", validation_alias=AliasChoices("is_consistent", "consistent", "isConsistent", "consistency"))
    conflict_points:  List[str]               = Field(default_factory=list, alias="conflict_points")
    severity:         Literal["Minor", "Major", "Critical"] = Field(default="Minor")
    audit_type:       Literal["Full", "Lightweight"] = Field(default="Full")
    rewrite_suggestion: str                   = Field(default="")

class LogicalAuditIssue(BaseModel):
    category: str = Field(default="その他")
    severity: Literal["Minor", "Major", "Critical"] = Field(default="Minor")
    description: str = Field(default="")
    evidence_current: str = Field(default="")
    constraint_for_next_ep: str = Field(default="")
    resolved: bool = Field(default=False)

    model_config = MODEL_CONFIG_DEFAULTS

class LogicalAuditIssueList(BaseModel):
    is_consistent: bool = Field(default=True)
    overall_severity: Literal["Minor", "Major", "Critical", "None"] = Field(default="None")
    issues: List[LogicalAuditIssue] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS

class RecoveredItem(BaseModel):
    foreshadowing_id: str = Field(default="", description="回収された伏線の説明やID")
    proof_text:      str = Field(default="", description="回収を証明する本文中の具体的なフレーズ")
    explanation:     str = Field(default="", description="どのように整合性が取られたかの解説")

class ForeshadowingAudit(BaseModel):
    """伏線回収の整合性監査結果"""
    is_recovered:     bool                    = Field(default=True, description="予定されていた伏線が回収されたか", validation_alias=AliasChoices("is_recovered", "recovered", "isRecovered"))
    recovered_items:  List[RecoveredItem]     = Field(default_factory=list, alias="recovered_items")
    missing_items:    List[str]               = Field(default_factory=list, description="未回収の伏線リスト")
    audit_type:       Literal["Full", "Lightweight"] = Field(default="Full")
    rewrite_suggestion: str                   = Field(default="")

    @model_validator(mode='before')
    @classmethod
    def validate_items(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # recovered_items が文字列のリストで来た場合、辞書形式に変換
            if "recovered_items" in data and isinstance(data["recovered_items"], list):
                data["recovered_items"] = [
                    {"foreshadowing_id": item} if isinstance(item, str) else item
                    for item in data["recovered_items"]
                ]
        return data


# ==========================================
# 演出コンテ・ストーリーボードモデル
# ==========================================


# ==========================================
# 作品構造サマリーモデル
# ==========================================
class NovelStructure(BaseModel):
    title:          str
    concept:        str
    synopsis:       str
    mc_profile:     CharacterRegistry        = Field(default_factory=CharacterRegistry)
    sub_characters: List[CharacterRegistry]  = Field(default_factory=list)
    plots:          List[PlotEpisode]        = Field(default_factory=list)
    marketing_assets: MarketingAssets        = Field(default_factory=MarketingAssets)
    anchors:        List[AnchorResponse]     = Field(default_factory=list)
    model_config = MODEL_CONFIG_DEFAULTS

# Resolve forward references
SceneBeatBlock.model_rebuild()
MasterSceneBlock.model_rebuild()
PlotEpisode.model_rebuild()
ForeshadowingAudit.model_rebuild()
WorldBible.model_rebuild()
NovelStructure.model_rebuild()

