from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationInfo, field_validator

from src.models.base import MODEL_CONFIG_DEFAULTS, ChainPhase


class PlotDbModel(BaseModel):
    book_id: int
    erotic_intensity: int = 0
    branch_id: int = 1
    ep_num: int
    thought_process: str | None = ""
    title: str | None = None
    summary: str | None = None
    detailed_blueprint: str | None = None
    tension: int | None = 50
    tension_delta: int | None = 0
    catharsis: int | None = 0
    status: str | None = None
    scenes: list[dict[str, Any]] | None = None
    is_catharsis: bool | None = False
    catharsis_type: str | None = None
    love_meter: int | None = 0
    next_hook: dict[str, Any] | None = None
    misunderstanding_gap: str | None = None
    lite_model_director_notes: str | None = None
    script_content: str | None = None
    current_chain_phase: ChainPhase | None = "Friction"
    resolution_style: str | None = "Cheat"
    burned_cost_or_loot: str | None = "なし"
    antagonist_status: str | None = "現状維持"
    thematic_milestone: str | None = "なし"
    state_integrity_score: int | None = 100
    healed_fields: list[str] | None = None
    is_micro_catharsis: bool | None = False
    information_asymmetry_level: float | None = 0.0
    cost_score: float | None = 0.0
    qol_delta: int | None = 0
    discovery_item: str | None = None
    sanctuary_event: str | None = None
    is_locked: bool | None = False
    emotional_resonance_score: int | None = 0
    thematic_depth_score: int | None = 0
    literary_beauty_score: int | None = 0
    emotional_hook_json: str | None = None
    sharp_edges_json: str | None = None
    quality_polish_status: str | None = None

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
