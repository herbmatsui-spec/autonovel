from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


class CharacterDbModel(BaseModel):
    id: int
    book_id: int
    name: Optional[str] = None
    role: Optional[str] = None
    registry_data: Optional[Union[dict, str]] = None

    def to_safe_dict(self) -> Dict[str, Any]:
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
