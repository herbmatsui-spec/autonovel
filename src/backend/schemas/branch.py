"""ブランチ管理用 FastAPI スキーマ."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models.base import MODEL_CONFIG_DEFAULTS


class BranchResponse(BaseModel):
    """単一ブランチのレスポンス."""

    id: int
    book_id: int
    name: str
    parent_id: int | None = None
    fork_ep_num: int | None = 0
    created_at: datetime | None = None

    model_config = MODEL_CONFIG_DEFAULTS


class BranchGraphResponse(BaseModel):
    """ブランチ配下の IF グラフ JSON レスポンス."""

    branch_id: int
    graph: dict[str, Any] = Field(default_factory=dict)

    model_config = MODEL_CONFIG_DEFAULTS


class BranchForkRequest(BaseModel):
    """フォーク（分岐作成）リクエスト."""

    parent_id: int
    name: str = Field(min_length=1, max_length=100)
    fork_ep_num: int = Field(default=0, ge=0)

    model_config = MODEL_CONFIG_DEFAULTS


class BranchMergeRequest(BaseModel):
    """マージ（合流）リクエスト.

    source_branch_id の plot を merge_ep_num で target_branch_id に合流させる。
    既存 IF グラフに MERGE ノードを追加する。
    """

    source_branch_id: int
    target_branch_id: int
    merge_ep_num: int = Field(ge=0)
    name: str | None = None

    model_config = MODEL_CONFIG_DEFAULTS
