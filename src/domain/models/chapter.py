from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from src.models.base import MODEL_CONFIG_DEFAULTS


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
