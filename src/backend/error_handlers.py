"""
src/backend/error_handlers.py - FastAPI統一エラーハンドラ (RFC 7807 Problem Details 準拠)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.backend.exceptions import AutoNovelException
from src.core.exceptions import HegemonyError

logger = logging.getLogger(__name__)


class ProblemDetailsResponse(BaseModel):
    """RFC 7807 準拠の構造化エラーレスポンス (後方互換フィールド付き)。"""

    type: str = Field(default="about:blank", description="エラー種別のURI識別子")
    title: str = Field(description="エラーの簡潔な要約")
    status: int = Field(description="HTTPステータスコード")
    detail: str | None = Field(default=None, description="エラーの詳細説明")
    instance: str | None = Field(default=None, description="エラーが発生したリクエストパス")
    # 後方互換フィールド
    success: bool = False
    error_code: str = "ERROR"
    error_message: str | None = None


ErrorResponse = ProblemDetailsResponse


async def autonovel_exception_handler(request: Request, exc: AutoNovelException) -> JSONResponse:
    """AutoNovel ドメイン例外ハンドラ"""
    logger.warning("AutoNovel Exception [%s]: %s", exc.__class__.__name__, exc.detail)
    content = ProblemDetailsResponse(
        type=f"urn:error:{exc.__class__.__name__.lower()}",
        title=exc.__class__.__name__,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        error_code=exc.__class__.__name__.upper(),
        error_message=exc.detail,
    ).model_dump()
    return JSONResponse(status_code=exc.status_code, content=content)


async def hegemony_error_handler(request: Request, exc: HegemonyError) -> JSONResponse:
    """Hegemony コアエラーハンドラ"""
    err_code = getattr(exc, "error_code", "INTERNAL_ERROR")
    msg = getattr(exc, "message", str(exc))
    status_code = getattr(exc, "status_code", 500)
    logger.warning("Hegemony Error [%s]: %s", err_code, msg)

    content = ProblemDetailsResponse(
        type=f"urn:error:{err_code.lower()}",
        title="Engine Error",
        status=status_code,
        detail=str(getattr(exc, "original", msg)),
        instance=str(request.url.path),
        error_code=err_code,
        error_message=msg,
    ).model_dump()
    return JSONResponse(status_code=status_code, content=content)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """リクエストバリデーションエラーハンドラ (422)"""
    logger.warning("Validation Error at %s: %s", request.url.path, exc.errors())
    content = ProblemDetailsResponse(
        type="urn:error:validation-error",
        title="Request Validation Error",
        status=422,
        detail=str(exc.errors()),
        instance=str(request.url.path),
        error_code="VALIDATION_ERROR",
        error_message="リクエストのバリデーションに失敗しました",
    ).model_dump()
    return JSONResponse(status_code=422, content=content)


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """未捕捉例外ハンドラ (500)"""
    logger.error("Unhandled error at %s: %s", request.url.path, exc, exc_info=True)
    content = ProblemDetailsResponse(
        type="urn:error:internal-server-error",
        title="Internal Server Error",
        status=500,
        detail=str(exc),
        instance=str(request.url.path),
        error_code="INTERNAL_ERROR",
        error_message="内部エラーが発生しました",
    ).model_dump()
    return JSONResponse(status_code=500, content=content)


def register_error_handlers(app: FastAPI) -> None:
    """FastAPIアプリにエラーハンドラを一括登録する"""
    app.add_exception_handler(AutoNovelException, autonovel_exception_handler)
    app.add_exception_handler(HegemonyError, hegemony_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

