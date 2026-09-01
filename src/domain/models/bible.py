from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


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
