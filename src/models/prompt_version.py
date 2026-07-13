from __future__ import annotations

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


class PromptVersionDbModel(BaseModel):
    """Pydantic model representing a prompt version record.

    Mirrors the SQLAlchemy ``PromptVersion`` ORM model defined in
    ``src/backend/database/models.py``. The fields are typed to reflect the
    database columns and provide safe defaults for optional values.
    """

    id: int
    book_id: Optional[int] = None
    prompt_key: str
    version_tag: str
    content: str
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    ab_test_metrics: Optional[Union[Dict[str, Any], str]] = None
    rollback_reason: Optional[str] = None
    is_active: bool = False
    created_at: Optional[str] = None

    # Compatibility shim for legacy code that expects a ``dict`` like ``get`` method
    def get(self, key: str, default: Any = None) -> Any:
        try:
            return getattr(self, key, default)
        except Exception:
            return default

    model_config = MODEL_CONFIG_DEFAULTS
