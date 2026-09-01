from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


class PromptVersionDbModel(BaseModel):
    """Pydantic model representing a prompt version record.

    Mirrors the SQLAlchemy ``PromptVersion`` ORM model defined in
    ``src/backend/database/models.py``. The fields are typed to reflect the
    database columns and provide safe defaults for optional values.
    """

    id: int
    book_id: int | None = None
    prompt_key: str
    version_tag: str
    content: str
    score_before: float | None = None
    score_after: float | None = None
    ab_test_metrics: dict[str, Any] | str | None = None
    rollback_reason: str | None = None
    is_active: bool = False
    created_at: datetime | None = None

    # Compatibility shim for legacy code that expects a ``dict`` like ``get`` method
    def get(self, key: str, default: Any = None) -> Any:
        try:
            return getattr(self, key, default)
        except Exception:
            return default

    model_config = MODEL_CONFIG_DEFAULTS
