from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


class BranchDbModel(BaseModel):
    """物語の分岐（Gitのブランチに相当）を管理するモデル"""

    id: int
    book_id: int
    name: str
    parent_id: int | None = None
    fork_ep_num: int | None = 0
    created_at: datetime | None = None

    model_config = MODEL_CONFIG_DEFAULTS
