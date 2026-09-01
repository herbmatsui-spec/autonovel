from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


class BookDbModel(BaseModel):
    id: int
    title: str
    genre: Optional[str] = None
    concept: Optional[str] = None
    synopsis: Optional[str] = None
    catchcopy: Optional[str] = None
    target_eps: Optional[int] = None
    style_dna: Optional[Union[dict, str]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    marketing_data: Optional[Union[dict, str]] = None
    cumulative_tension: Optional[int] = 0
    cumulative_qol: Optional[int] = 0
    cumulative_cost: Optional[float] = 0.0
    sanctuary_integrity: Optional[int] = 100
    current_branch_id: Optional[int] = None

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
