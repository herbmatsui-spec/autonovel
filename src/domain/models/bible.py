from __future__ import annotations

import json
from typing import Any, Optional, Union

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


class BibleDbModel(BaseModel):
    id: int
    book_id: int
    settings: Optional[Union[dict, str]] = None
    revealed: Optional[str] = None
    version: Optional[int] = None
    last_updated: Optional[str] = None

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
