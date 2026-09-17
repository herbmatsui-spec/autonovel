"""RFC 7807 Problem Details スキーマ。"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    """RFC 7807 に準拠した構造化エラーレスポンス。"""
    type: str = Field(
        default="about:blank",
        description="エラー種別を識別するURI参照",
    )
    title: str = Field(
        ...,
        description="人間が読める簡潔なエラー要約",
    )
    status: int = Field(
        ...,
        description="HTTPステータスコード",
    )
    detail: Optional[str] = Field(
        default=None,
        description="この発生インスタンスに特有の人道的な詳細説明",
    )
    instance: Optional[str] = Field(
        default=None,
        description="エラーが発生した具体的なリソースまたはリクエストパス",
    )
    invalid_params: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="バリデーションエラー時のフィールド別詳細",
    )
