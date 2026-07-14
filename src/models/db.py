from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ValidationInfo, field_validator

from src.models.base import MODEL_CONFIG_DEFAULTS, ChainPhase


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
    created_at:       Optional[datetime]         = None
    marketing_data:   Optional[Union[dict, str]] = None
    cumulative_tension: Optional[int]             = 0
    cumulative_qol:    Optional[int]             = 0
    cumulative_cost:   Optional[float]           = 0.0
    sanctuary_integrity: Optional[int]           = 100
    current_branch_id: Optional[int]             = None

    @property
    def style_key(self) -> str:
        """style_dna からスタイルキー（mode）を安全に取得する"""
        if isinstance(self.style_dna, dict):
            return self.style_dna.get("mode", "default")
        if isinstance(self.style_dna, str) and self.style_dna.strip():
            try:
                data = json.loads(self.style_dna)
                return data.get("mode", "default")
            except (json.JSONDecodeError, TypeError):
                return "default"
        return "default"

    model_config = MODEL_CONFIG_DEFAULTS

class BibleDbModel(BaseModel):
    id:           int
    book_id:      int
    settings:     Optional[Union[dict, str]] = None
    revealed:     Optional[str]              = None
    version:      Optional[int]              = None
    last_updated: Optional[str]              = None

    @property
    def world_settings(self) -> Any:
        """settings から WorldRules 相当のデータを取得する。"""
        if isinstance(self.settings, dict):
            return self.settings
        if isinstance(self.settings, str) and self.settings.strip():
            try:
                return json.loads(self.settings)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    model_config = MODEL_CONFIG_DEFAULTS

class BranchDbModel(BaseModel):
    """物語の分岐（Gitのブランチに相当）を管理するモデル"""
    id:               int
    book_id:          int
    name:             str
    parent_id:        Optional[int] = None
    fork_ep_num:      Optional[int] = 0
    created_at:       Optional[datetime] = None

    model_config = MODEL_CONFIG_DEFAULTS

class PlotDbModel(BaseModel):
    book_id:                   int
    erotic_intensity:          int = 0
    branch_id:                 int                        = 1
    ep_num:                    int
    thought_process:           Optional[str]              = ""
    title:                     Optional[str]              = None
    summary:                   Optional[str]              = None
    detailed_blueprint:        Optional[str]              = None
    tension:                   Optional[int]              = 50
    tension_delta:             Optional[int]              = 0
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
    current_chain_phase:       Optional[ChainPhase]       = "Friction"
    resolution_style:          Optional[str]              = "Cheat"
    burned_cost_or_loot:       Optional[str]              = "なし"
    antagonist_status:         Optional[str]              = "現状維持"
    thematic_milestone:        Optional[str]              = "なし"
    state_integrity_score:     Optional[int]              = 100
    healed_fields:             Optional[List[str]]        = None
    is_micro_catharsis:        Optional[bool]             = False
    information_asymmetry_level: Optional[float]           = 0.0
    cost_score:                Optional[float]            = 0.0
    qol_delta:                 Optional[int]              = 0
    discovery_item:            Optional[str]              = None
    sanctuary_event:           Optional[str]              = None
    is_locked:                 Optional[bool]             = False
    emotional_resonance_score: Optional[int]              = 0
    thematic_depth_score:      Optional[int]              = 0
    literary_beauty_score:     Optional[int]              = 0
    emotional_hook_json:       Optional[str]              = None
    sharp_edges_json:          Optional[str]              = None
    quality_polish_status:     Optional[str]              = None

    @field_validator("next_hook", "scenes", mode="before")
    @classmethod
    def ensure_structured_data(cls, v: Any, info: ValidationInfo) -> Any:
        """DBから読み込む際の文字列化されたJSONをパースし、構造化データとして保持する。"""
        if not v:
            return [] if info.field_name == "scenes" else {}
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

    model_config = MODEL_CONFIG_DEFAULTS

class ChapterDbModel(BaseModel):
    book_id:           int
    branch_id:         int                        = 1
    ep_num:            int
    title:             Optional[str]              = None
    content:           Optional[str]              = None
    score_story:       Optional[int]              = None
    killer_phrase:     Optional[str]              = None
    summary:           Optional[str]              = None
    world_state:       Optional[Union[dict, str]] = None
    trinity_review_log: Optional[Union[dict, str]] = None
    ai_insight:        Optional[str]              = None
    created_at:        Optional[datetime]         = None
    tension_delta:      Optional[int]              = 0
    qol_delta:         Optional[int]              = 0

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

    model_config = MODEL_CONFIG_DEFAULTS

class CharacterDbModel(BaseModel):
    id:            int
    book_id:       int
    name:          Optional[str]              = None
    role:          Optional[str]              = None
    registry_data: Optional[Union[dict, str]] = None

    def to_safe_dict(self) -> Dict[str, Any]:
        """registry_data を辞書として安全に取得する。文字列の場合は JSON パースを行う。"""
        if isinstance(self.registry_data, dict):
            return self.registry_data
        if isinstance(self.registry_data, str) and self.registry_data.strip():
            try:
                return json.loads(self.registry_data)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    model_config = MODEL_CONFIG_DEFAULTS
