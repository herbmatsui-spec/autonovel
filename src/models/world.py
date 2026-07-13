from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator

from src.models.base import MODEL_CONFIG_DEFAULTS


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

class ClimaxScene(BaseModel):
    timing:               str = Field(default="", description="発生予定の話数やタイミング。例: '第10話 決戦時'")
    event:                str = Field(default="", description="名場面の内容。何が起き、誰がどうなり、どのようなカタルシスがあるか")
    target_emotion:       str = Field(default="", description="読者に抱かせたい感情（例：絶望、鳥肌が立つような爽快感、感動の涙）")
    pre_written_dialogue: str = Field(default="", description="決定的なセリフの応酬（魂の対話）")

class WorldRules(BaseModel):
    magic_cost_and_taboo:          str             = Field(default="なし", description="魔法やスキルの残酷な代償と世界の禁忌")
    social_hierarchy_and_discrimination: str       = Field(default="なし", description="主人公が迫害される絶対的な社会的構造")
    hidden_truths:                 Dict[str, str]  = Field(default_factory=dict, description="絶望的な真実・最大の伏線を3つ以上")
    truth_ledger:                  Dict[str, Any]  = Field(default_factory=dict, description="物語の根幹に関わる真実のデータベース")
    geopolitics_and_economy:       str             = Field(default="なし", description="資源の偏り、通貨の価値、地政学的緊張")
    religious_dogma_and_heresy:    str             = Field(default="なし", description="信仰と、それを破った際の社会的制裁")
    causality_map:                 List[str]       = Field(default_factory=list, description="設定間の不可避な因果律の連鎖（AがBを生み、Cに繋がる等）")
    foreshadowing_map:             List[Foreshadowing] = Field(default_factory=list)
    active_constraints:            List[NarrativeConstraint] = Field(default_factory=list, description="現在有効な論理制約リスト")
    climax_scenes:                 List[ClimaxScene]   = Field(default_factory=list, description="読者の心を揺さぶる名場面(3〜5個)")
    mystery_disclosure_schedule:   List[Dict[str, Any]] = Field(default_factory=list)
    tension_threshold:             int             = Field(default=85)
    tension_gain:                  float           = Field(default=1.0)
    memory_integrity_score:        int             = Field(default=100, description="作品全体の精神的整合性初期値")
    location_sensory_map:          Dict[str, Dict[str, str]] = Field(default_factory=dict, description="場所・環境別の生理描写オーバーレイ辞書（場所名 -> {感情名: 置換描写}）")

    # --- Comfort Engine Core Settings ---
    initial_qol_score:           int = Field(default=0)
    initial_sanctuary_integrity: int = Field(default=100)

    @model_validator(mode="before")
    @classmethod
    def unwrap_world_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "world", "rules", "settings"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # Heal single dictionary to list for list-of-objects fields
            for list_field in ["active_constraints", "foreshadowing_map", "climax_scenes", "mystery_disclosure_schedule"]:
                if list_field in data:
                    val = data[list_field]
                    if isinstance(val, dict):
                        data[list_field] = [val]
                    elif val is None:
                        data[list_field] = []

            # Heal causality_map string to List[str] if needed
            if "causality_map" in data:
                val = data["causality_map"]
                if isinstance(val, str):
                    if "\n" in val:
                        data["causality_map"] = [line.strip("- *").strip() for line in val.split("\n") if line.strip()]
                    elif "→" in val:
                        data["causality_map"] = [part.strip() for part in val.split("→") if part.strip()]
                    elif "->" in val:
                        data["causality_map"] = [part.strip() for part in val.split("->") if part.strip()]
                    elif "、" in val:
                        data["causality_map"] = [part.strip() for part in val.split("、") if part.strip()]
                    elif "," in val:
                        data["causality_map"] = [part.strip() for part in val.split(",") if part.strip()]
                    else:
                        data["causality_map"] = [val.strip()]
                elif isinstance(val, list):
                    # Ensure all elements are strings
                    data["causality_map"] = [str(x) for x in val]
        return data


class AnchorResponse(BaseModel):
    anchor_id: str = Field(default="", description="アンカーID")
    content: str = Field(default="", description="確定した事実や設定の内容")
    category: str = Field(default="General", description="カテゴリ")
    importance: int = Field(default=3, ge=1, le=5)

    # --- Comfort Engine Metrics ---
    qol_score:           int = Field(default=0, description="生活の質（0-1000）")
    sanctuary_integrity: int = Field(default=100, description="聖域の堅牢性（0-100）")
    discovery_logs:      List[Dict[str, Any]] = Field(default_factory=list, description="発見された素材・技術の履歴")

    # --- Enigma Engine Metrics ---
    intellectual_satisfaction: int = Field(default=0, description="知的充足度（0-100）")
    mystery_density:           int = Field(default=0, description="現在の謎の累積度（0-100）")
    strategic_depth:           int = Field(default=100, description="戦略的優位性/深度（0-100）")

    model_config = MODEL_CONFIG_DEFAULTS

class StoryThread(BaseModel):
    id:                    str     = Field(..., description="スレッドID")
    description:           str     = Field(..., description="内容")
    status:                Literal["Active", "Dormant", "Resolving", "Closed"] = Field(default="Active")
    urgency:               int     = Field(default=1, ge=1, le=5)
    setup_episode:         int     = Field(..., description="発生話数")
    target_resolve_episode: Optional[int] = Field(default=None)

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
    memory_integrity_score: int             = Field(default=100, ge=0, le=100, description="精神的整合性スコア。0で文章が完全崩壊する")

    # --- Comfort Engine Dynamic State ---
    qol_score:           int = Field(default=0, description="現在の生活の質")
    sanctuary_integrity: int = Field(default=100, description="現在の聖域の堅牢性")
    veneration_level:    float = Field(default=0.0, description="周囲からの崇拝度・神格化レベル (0.0 - 1.0)")
    fulfillment_matrix:  Dict[str, float] = Field(default_factory=lambda: {"cuisine": 0.0, "craft": 0.0, "nature": 0.0, "relation": 0.0}, description="多次元的充足指標（CCTに基づく）")
    sanctuary_expansion_rate: float = Field(default=1.0, description="聖域の物理的・心理的拡張範囲")
    discovery_logs:      List[Dict[str, Any]] = Field(default_factory=list, description="発見履歴")

class RecoveredItem(BaseModel):
    foreshadowing_id: str = Field(default="", description="回収された伏線の説明やID")
    proof_text:      str = Field(default="", description="回収を証明する本文中の具体的なフレーズ")
    explanation:     str = Field(default="", description="どのように整合性が取られたかの解説")

class ForeshadowingAudit(BaseModel):
    """伏線回収の整合性監査結果"""
    is_recovered:     bool                    = Field(default=True, description="予定されていた伏線が回収されたか", validation_alias=AliasChoices("is_recovered", "recovered", "isRecovered"))
    recovered_items:  List[RecoveredItem]     = Field(default_factory=list)
    missing_items:    List[str]               = Field(default_factory=list, description="未回収の伏線リスト")
    audit_type:       Literal["Full", "Lightweight"] = Field(default="Full")
    rewrite_suggestion: str                   = Field(default="")

    @model_validator(mode='before')
    @classmethod
    def unwrap_and_validate_items(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Wrapper peeling
            for wrapper in ["metadata", "data", "audit", "result"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # 2. recovered_items が文字列のリストで来た場合、辞書形式に変換
            if "recovered_items" in data and isinstance(data["recovered_items"], list):
                data["recovered_items"] = [
                    {"foreshadowing_id": item} if isinstance(item, str) else item
                    for item in data["recovered_items"]
                ]

            # 3. Default injections
            if "is_recovered" not in data and not any(a in data for a in ["recovered", "isRecovered"]):
                data["is_recovered"] = True
        return data

    model_config = MODEL_CONFIG_DEFAULTS
