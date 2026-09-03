"""IF プレイヤーセッション用 FastAPI スキーマ."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models.base import MODEL_CONFIG_DEFAULTS


class BranchPlayRequest(BaseModel):
    """セッション開始リクエスト."""

    book_id: int = Field(ge=1)
    branch_id: int = Field(ge=1)

    model_config = MODEL_CONFIG_DEFAULTS


class BranchPlaySessionResponse(BaseModel):
    """セッション作成 / 終了レスポンス."""

    session_id: str
    book_id: int
    branch_id: int
    current_node_id: str | None = None
    status: str = "active"
    updated_at: datetime | None = None

    model_config = MODEL_CONFIG_DEFAULTS


class BranchPlayStateResponse(BaseModel):
    """現セッション状態."""

    session_id: str
    book_id: int
    branch_id: int
    current_node: dict[str, Any] = Field(default_factory=dict)
    current_node_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    available_choices: list[dict[str, Any]] = Field(default_factory=list)
    save_points_count: int = 0
    status: str = "active"
    updated_at: datetime | None = None

    model_config = MODEL_CONFIG_DEFAULTS


class BranchPlayChooseRequest(BaseModel):
    """選択肢実行リクエスト."""

    choice_id: str = Field(min_length=1)

    model_config = MODEL_CONFIG_DEFAULTS


class BranchPlayEndRequest(BaseModel):
    """セッション終了リクエスト."""

    status: str = Field(default="completed")

    model_config = MODEL_CONFIG_DEFAULTS


class BranchPlayPlaythroughResponse(BaseModel):
    """プレイスルー記録レスポンス."""

    session_id: str
    book_id: int
    branch_id: int
    history: list[Any] = Field(default_factory=list)
    flags: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    final_ending: str | None = None
    saved_at: datetime | None = None

    model_config = MODEL_CONFIG_DEFAULTS
