from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.models.base import MODEL_CONFIG_DEFAULTS


class BranchDbModel(BaseModel):
    """物語の分岐（Gitのブランチに相当）を管理するモデル"""

    id: int
    book_id: int
    name: str
    parent_id: Optional[int] = None
    fork_ep_num: Optional[int] = 0
    created_at: Optional[datetime] = None

    model_config = MODEL_CONFIG_DEFAULTS
