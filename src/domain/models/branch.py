from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models.base import MODEL_CONFIG_DEFAULTS


class BranchDbModel(BaseModel):
    """物語の分岐（Gitのブランチに相当）を管理するモデル"""

    id: int
    book_id: int
    name: str
    parent_id: int | None = None
    fork_ep_num: int | None = 0
    graph_json: dict[str, Any] | None = None
    created_at: datetime | None = None

    model_config = MODEL_CONFIG_DEFAULTS


class BranchDbModelCreate(BaseModel):
    """新規ブランチ作成用リクエスト."""

    book_id: int
    name: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None
    fork_ep_num: int | None = 0
    graph_json: dict[str, Any] | None = None

    model_config = MODEL_CONFIG_DEFAULTS


class BranchDbModelUpdate(BaseModel):
    """ブランチ更新用リクエスト."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    fork_ep_num: int | None = None
    graph_json: dict[str, Any] | None = None

    model_config = MODEL_CONFIG_DEFAULTS
