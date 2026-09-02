from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationInfo, field_validator

from src.models.base import MODEL_CONFIG_DEFAULTS, ChainPhase


class BookDbModel(BaseModel):
    id: int
    title: str
    genre: str | None = None
    concept: str | None = None
    synopsis: str | None = None
    catchcopy: str | None = None
    target_eps: int | None = None
    style_dna: dict | str | None = None
    status: str | None = None
    created_at: datetime | None = None
    marketing_data: dict | str | None = None
    cumulative_tension: int | None = 0
    cumulative_qol: int | None = 0
    cumulative_cost: float | None = 0.0
    sanctuary_integrity: int | None = 100
    current_branch_id: int | None = None

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
    id: int
    book_id: int
    settings: dict | str | None = None
    revealed: str | None = None
    version: int | None = None
    last_updated: str | None = None

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

    id: int
    book_id: int
    name: str
    parent_id: int | None = None
    fork_ep_num: int | None = 0
    created_at: datetime | None = None

    model_config = MODEL_CONFIG_DEFAULTS


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


class ChapterDbModel(BaseModel):
    book_id: int
    branch_id: int = 1
    ep_num: int
    title: str | None = None
    content: str | None = None
    score_story: int | None = None
    killer_phrase: str | None = None
    summary: str | None = None
    world_state: dict | str | None = None
    trinity_review_log: dict | str | None = None
    ai_insight: str | None = None
    created_at: datetime | None = None
    tension_delta: int | None = 0
    qol_delta: int | None = 0

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
    id: int
    book_id: int
    name: str | None = None
    role: str | None = None
    registry_data: dict | str | None = None

    def to_safe_dict(self) -> dict[str, Any]:
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
