from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationInfo, field_validator

from src.models.base import MODEL_CONFIG_DEFAULTS, ChainPhase


class PlotDbModel(BaseModel):
    book_id: int
    erotic_intensity: int = 0
    branch_id: int = 1
    ep_num: int
    thought_process: Optional[str] = ""
    title: Optional[str] = None
    summary: Optional[str] = None
    detailed_blueprint: Optional[str] = None
    tension: Optional[int] = 50
    tension_delta: Optional[int] = 0
    catharsis: Optional[int] = 0
    status: Optional[str] = None
    scenes: Optional[List[Dict[str, Any]]] = None
    is_catharsis: Optional[bool] = False
    catharsis_type: Optional[str] = None
    love_meter: Optional[int] = 0
    next_hook: Optional[Dict[str, Any]] = None
    misunderstanding_gap: Optional[str] = None
    lite_model_director_notes: Optional[str] = None
    script_content: Optional[str] = None
    current_chain_phase: Optional[ChainPhase] = "Friction"
    resolution_style: Optional[str] = "Cheat"
    burned_cost_or_loot: Optional[str] = "なし"
    antagonist_status: Optional[str] = "現状維持"
    thematic_milestone: Optional[str] = "なし"
    state_integrity_score: Optional[int] = 100
    healed_fields: Optional[List[str]] = None
    is_micro_catharsis: Optional[bool] = False
    information_asymmetry_level: Optional[float] = 0.0
    cost_score: Optional[float] = 0.0
    qol_delta: Optional[int] = 0
    discovery_item: Optional[str] = None
    sanctuary_event: Optional[str] = None
    is_locked: Optional[bool] = False
    emotional_resonance_score: Optional[int] = 0
    thematic_depth_score: Optional[int] = 0
    literary_beauty_score: Optional[int] = 0
    emotional_hook_json: Optional[str] = None
    sharp_edges_json: Optional[str] = None
    quality_polish_status: Optional[str] = None

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
