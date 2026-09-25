"""
Social reaction data schemas for streaming comments and forum posts.
PLAN 02: エンタメ演出強化・マルチジャンル＆配信・掲示板演出
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime


class StreamComment(BaseModel):
    """単一の配信コメント"""
    user: str = Field(..., description="コメントしたユーザー名")
    text: str = Field(..., description="コメント内容")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="コメントタイムスタンプ")


class ForumPost(BaseModel):
    """掲示板の単一レス"""
    res_num: int = Field(..., description="レス番号")
    name: str = Field(..., description="ハンドルネーム")
    body: str = Field(..., description="レス本文")