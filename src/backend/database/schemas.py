import json
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from src.models.base import ChainPhase

# ==========================================
# DB操作用Pydanticモデル（database/models.pyのSQLAlchemyモデルと対応）
# ==========================================

class BookSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    genre: Optional[str] = None
    concept: Optional[str] = None
    synopsis: Optional[str] = None
    catchcopy: Optional[str] = None
    target_eps: Optional[int] = None
    style_dna: Optional[Union[dict, str]] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    marketing_data: Optional[Union[dict, str]] = None
    cumulative_tension: Optional[int] = 0

class BibleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    settings: Optional[Union[dict, str]] = None
    revealed: Optional[str] = None
    version: Optional[int] = None
    last_updated: Optional[str] = None

class PlotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    erotic_intensity: Optional[int] = 0

    book_id: int
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
    emotional_resonance_score: Optional[int] = 0
    thematic_depth_score: Optional[int] = 0
    literary_beauty_score: Optional[int] = 0

    @field_validator("next_hook", "scenes", mode="before")
    @classmethod
    def ensure_structured_data(cls, v: Any, info: ValidationInfo) -> Any:
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                if info.field_name == "scenes":
                    return [{"action": v}]
                elif info.field_name == "next_hook":
                    return {"description": v}
                return v
        return v

class ChapterSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    book_id: int
    ep_num: int
    title: Optional[str] = None
    content: Optional[str] = None
    score_story: Optional[int] = None
    killer_phrase: Optional[str] = None
    summary: Optional[str] = None
    world_state: Optional[Union[dict, str]] = None
    trinity_review_log: Optional[Union[dict, str]] = None
    ai_insight: Optional[str] = None
    created_at: Optional[str] = None

    @field_validator("world_state", "trinity_review_log", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip():
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {"raw_data": parsed}
            except (json.JSONDecodeError, TypeError):
                return {"raw_info": v}
        if v is None:
            return {}
        return v

class CharacterSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    name: Optional[str] = None
    role: Optional[str] = None
    registry_data: Optional[Union[dict, str]] = None

