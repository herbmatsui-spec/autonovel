from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, field_validator

from src.models.base import MODEL_CONFIG_DEFAULTS


class ChapterDbModel(BaseModel):
    book_id: int
    branch_id: int = 1
    ep_num: int
    title: Optional[str] = None
    content: Optional[str] = None
    score_story: Optional[int] = None
    killer_phrase: Optional[str] = None
    summary: Optional[str] = None
    world_state: Optional[Union[dict, str]] = None
    trinity_review_log: Optional[Union[dict, str]] = None
    ai_insight: Optional[str] = None
    created_at: Optional[datetime] = None
    tension_delta: Optional[int] = 0
    qol_delta: Optional[int] = 0

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
