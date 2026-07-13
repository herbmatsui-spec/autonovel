from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    model_validator,
)

MODEL_CONFIG_DEFAULTS = {
    "populate_by_name": True,
    "extra": "allow",
    "protected_namespaces": ()
}

class CharacterRelationship(BaseModel):
    target_char_name: str = Field(default="不明")
    type: str = Field(default="関係者")
    model_config = MODEL_CONFIG_DEFAULTS

class CharacterRegistry(BaseModel):
    name:                Optional[str]   = Field(default="", validation_alias=AliasChoices("name", "char_name", "character_name"))
    role:                Optional[str]   = Field(default="", validation_alias=AliasChoices("role", "position", "job", "class"))
    gender:              Optional[str]   = Field(default="")
    age:                 Optional[str]   = Field(default="")
    appearance:          Optional[str]   = Field(default="", validation_alias=AliasChoices("appearance", "visual", "look"))
    personality:         Optional[str]   = Field(default="", validation_alias=AliasChoices("personality", "traits", "character", "nature"))
    surface_persona:     Optional[str]   = Field(default="", description="周囲からどう見られているか、演じている役割")
    inner_conflict:      Optional[str]   = Field(default="", description="演じている自分と本当の望みの間の葛藤")
    core_trauma:         Optional[str]   = Field(default="", description="過去のトラウマや原初の欠落")
    save_the_cat_event:  Optional[str]   = Field(default="", description="読者が共感する人間味ある善行")
    first_person:        Optional[str]   = Field(default="私", description="一人称", validation_alias=AliasChoices("first_person", "fp", "i", "first"))
    second_person:       Optional[str]   = Field(default="貴方", description="二人称", validation_alias=AliasChoices("second_person", "sp", "you", "second"))
    suffix_style:        Optional[str]   = Field(default="", description="特徴的な語尾", validation_alias=AliasChoices("suffix_style", "suffix", "style"))
    ability:             Optional[str]   = Field(default="", validation_alias=AliasChoices("ability", "power", "skill", "magic"))
    background:          Optional[str]   = Field(default="", validation_alias=AliasChoices("background", "bg", "history", "story"))
    tone:                Optional[str]   = Field(default="", validation_alias=AliasChoices("tone", "voice", "manner"))
    iron_constraint:     Optional[str]   = Field(default="", description="絶対に破らない行動原則・禁忌", validation_alias=AliasChoices("iron_constraint", "iron_const", "rule", "taboo"))
    fate_link:           Optional[str]   = Field(default="", description="世界の因果律との繋がり")
    social_mask_vs_truth: Optional[str]   = Field(default="", description="表向きの社会的仮面と、夜一人でいる時に見せる剥き出しの真実の対比")
    pronouns:            Dict[str, str]  = Field(default_factory=dict)
    relationships:       List[CharacterRelationship] = Field(default_factory=list, validation_alias=AliasChoices("relationships", "relations", "rels"))
    dialogue_samples:    List[str]       = Field(default_factory=list, validation_alias=AliasChoices("dialogue_samples", "dlg_smp", "samples", "quotes"))
    keywords:            List[str]       = Field(default_factory=list, validation_alias=AliasChoices("keywords", "kws", "tags"))
    expansion_hooks:     List[str]       = Field(default_factory=list, validation_alias=AliasChoices("expansion_hooks", "exp_hooks", "hooks", "hooks_list"), description="描写を膨らせるための固有要素")

    model_config = MODEL_CONFIG_DEFAULTS

    @model_validator(mode="before")
    @classmethod
    def unwrap_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for wrapper in ["metadata", "data", "character", "profile"]:
                if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                    data = data[wrapper]
                    break

            str_fields = [
                "name", "role", "gender", "age", "appearance", "personality",
                "surface_persona", "inner_conflict", "core_trauma", "save_the_cat_event",
                "first_person", "second_person", "suffix_style", "ability",
                "background", "tone", "iron_constraint", "fate_link", "social_mask_vs_truth"
            ]
            for f in str_fields:
                if f not in data:
                    data[f] = data.get(f, "私" if f == "first_person" else "貴方" if f == "second_person" else "")
        return data

class WorldBibleCore(BaseModel):
    mc_profile: CharacterRegistry = Field(default_factory=CharacterRegistry)

# Test
try:
    print("Testing empty dict for WorldBibleCore...")
    # This simulates what happens in engine_agents.py:381
    res = WorldBibleCore.model_validate({"mc_profile": {}})
    print(f"Success! MC Profile name: '{res.mc_profile.name}', Iron constraint: '{res.mc_profile.iron_constraint}'")
except Exception as e:
    print(f"Failed: {e}")

