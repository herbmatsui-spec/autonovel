from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from src.models.base import MODEL_CONFIG_DEFAULTS, extract_int


class CharacterConcept(BaseModel):
    """キャラクターの初期コンセプト案"""
    name:            str             = Field(..., description="キャラクター名（仮）")
    trait:           str             = Field(..., description="特性・二つ名")
    core_idea:       str             = Field(..., description="コアコンセプト・核心")
    appeal_point:    str             = Field(..., description="読者への訴求点・カタルシス要素")
    villain_concept: Optional[str]   = Field(default=None, description="想定される敵対者像")

    model_config = MODEL_CONFIG_DEFAULTS

class CharacterConceptList(BaseModel):
    """キャラクターコンセプト案のリスト"""
    concepts: List[CharacterConcept] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def unwrap_concepts_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "results", "character"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break
        return data

    model_config = MODEL_CONFIG_DEFAULTS

class CharacterRelationship(BaseModel):
    target_char_name: str = Field(
        default="不明",
        description="関係性を持つ相手のキャラクター名",
        validation_alias=AliasChoices("target_char_name", "target", "name", "to", "char")
    )
    type: str = Field(
        default="関係者",
        description="関係性の種類（例: ライバル, 師弟, 依存, 秘密の恋人, 恩人, 宿敵）",
        validation_alias=AliasChoices("type", "relation", "relationship", "relation_type", "kind", "role", "label")
    )
    description: str = Field(default="", description="関係性の具体的な内容や背景")
    intensity: int = Field(default=3, ge=1, le=5, description="関係性の強度（1:弱い〜5:強い）")
    secret_aspect: Optional[str] = Field(default=None, description="関係性の秘密の側面や裏の顔")

    model_config = MODEL_CONFIG_DEFAULTS

    @model_validator(mode="before")
    @classmethod
    def unwrap_rel_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "relationship", "relation"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # 数値を含む可能性のあるスコア辞書の正規化
            if "scores" in data and isinstance(data["scores"], dict):
                for k, v in data["scores"].items():
                    if isinstance(v, str):
                        data["scores"][k] = extract_int(v)
        return data

class CharacterRegistry(BaseModel):
    name:                str             = Field(default="", validation_alias=AliasChoices("name", "char_name", "character_name"))
    role:                str             = Field(default="", validation_alias=AliasChoices("role", "position", "job", "class"))
    gender:              str             = Field(default="")
    age:                 str             = Field(default="")
    appearance:          str             = Field(default="", validation_alias=AliasChoices("appearance", "visual", "look"))
    personality:         str             = Field(default="", validation_alias=AliasChoices("personality", "traits", "character", "nature"))
    surface_persona:     str             = Field(default="", description="周囲からどう見られているか、演じている役割")
    inner_conflict:      str             = Field(default="", description="演じている自分と本当の望みの間の葛藤")
    core_trauma:         str             = Field(default="", description="過去のトラウマや原初の欠落")
    save_the_cat_event:  str             = Field(default="", description="読者が共感する人間味ある善行")
    first_person:        str             = Field(default="私", description="一人称", validation_alias=AliasChoices("first_person", "fp", "i", "first"))
    second_person:       str             = Field(default="貴方", description="二人称", validation_alias=AliasChoices("second_person", "sp", "you", "second"))
    suffix_style:        str             = Field(default="", description="特徴的な語尾", validation_alias=AliasChoices("suffix_style", "suffix", "style"))
    suffix_patterns:     List[str]       = Field(default_factory=list, description="語尾検証用の正規表現パターン（例: ['〜だわ$', '〜ですわ$']）")
    known_facts:         List[str]       = Field(default_factory=list, description="このキャラが知っている事実（Truth Ledger）")
    unknown_facts:       List[str]       = Field(default_factory=list, description="このキャラが知らない事実（会話で漏らしてはいけない）")
    ability:             str             = Field(default="", validation_alias=AliasChoices("ability", "power", "skill", "magic"))
    background:          str             = Field(default="", validation_alias=AliasChoices("background", "bg", "history", "story"))
    tone:                str             = Field(default="", validation_alias=AliasChoices("tone", "voice", "manner"))
    iron_constraint:     str             = Field(default="", description="絶対に破らない行動原則・禁忌", validation_alias=AliasChoices("iron_constraint", "iron_const", "rule", "taboo"))
    fate_link:           str             = Field(default="", description="世界の因果律との繋がり")
    social_mask_vs_truth: str            = Field(default="", description="表向きの社会的仮面と、夜一人でいる時に見せる剥き出しの真実の対比")
    pronouns:            Dict[str, str]  = Field(default_factory=dict)
    relationships:       List[CharacterRelationship] = Field(default_factory=list, validation_alias=AliasChoices("relationships", "relations", "rels"))
    dialogue_samples:    List[str]       = Field(default_factory=list, validation_alias=AliasChoices("dialogue_samples", "dlg_smp", "samples", "quotes"))
    keywords:            List[str]       = Field(default_factory=list, validation_alias=AliasChoices("keywords", "kws", "tags"))
    expansion_hooks:     List[str]       = Field(default_factory=list, validation_alias=AliasChoices("expansion_hooks", "exp_hooks", "hooks", "hooks_list"), description="描写を膨らせるための固有要素")

    model_config = MODEL_CONFIG_DEFAULTS

    @model_validator(mode="before")
    @classmethod
    def unwrap_metadata(cls, data: Any) -> Any:
        """AIが返す metadata/data/character 等のラッパーを剥がし、欠落フィールドを補填する"""
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "character", "profile"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            # [FIX] Pydantic V2 の Alias + Default 不整合対策
            # LLMが不完全な構造を返した場合でも、バリデーションエラーを防ぐために空文字を注入する。
            # ただし、エイリアスが既に存在する場合は上書きしないように修正。
            str_fields = {
                "name": ["name", "char_name", "character_name"],
                "role": ["role", "position", "job", "class"],
                "gender": ["gender"],
                "age": ["age"],
                "appearance": ["appearance", "visual", "look"],
                "personality": ["personality", "traits", "character", "nature"],
                "surface_persona": ["surface_persona"],
                "inner_conflict": ["inner_conflict"],
                "core_trauma": ["core_trauma"],
                "save_the_cat_event": ["save_the_cat_event"],
                "first_person": ["first_person", "fp", "i", "first"],
                "second_person": ["second_person", "sp", "you", "second"],
                "suffix_style": ["suffix_style", "suffix", "style"],
                "ability": ["ability", "power", "skill", "magic"],
                "background": ["background", "bg", "history", "story"],
                "tone": ["tone", "voice", "manner"],
                "iron_constraint": ["iron_constraint", "iron_const", "rule", "taboo"],
                "fate_link": ["fate_link"],
                "social_mask_vs_truth": ["social_mask_vs_truth"]
            }
            for f, aliases in str_fields.items():
                if not any(a in data for a in aliases):
                    data[f] = "私" if f == "first_person" else "貴方" if f == "second_person" else ""
        return data

    @field_validator("keywords", "dialogue_samples", "expansion_hooks", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> Any:
        """文字列、None、または単一オブジェクトが来た場合にリストに変換・正規化する"""
        if isinstance(v, str):
            # カンマ、読点、改行で分割してリスト化
            return [x.strip() for x in re.split(r'[,、\n]', v) if x.strip()]
        if v is None:
            return []
        if not isinstance(v, list):
            return [str(v)]
        return v

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
        rels_list = [r.model_dump() if hasattr(r, "model_dump") else r for r in (self.relationships or [])]
        rels_str = _json.dumps(rels_list, ensure_ascii=False)
        prompt += f"- Rels: {rels_str}\n"
        prompt += f"- DlgSmp: {_json.dumps(self.dialogue_samples, ensure_ascii=False)}\n"
        return prompt

    @classmethod
    def from_db(cls, data: Union[dict, str]) -> CharacterRegistry:
        """DBからの復元時に型変換を安全に行う"""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {}
        return cls.model_validate(data) if isinstance(data, dict) else cls()
