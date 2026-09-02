from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


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
