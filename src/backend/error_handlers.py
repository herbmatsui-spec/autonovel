"""
src/backend/error_handlers.py - FastAPI統一エラーハンドラ
"""
import logging
from typing import Optional
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from src.core.exceptions import HegemonyError

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """統一エラーレスポンス"""

    success: bool = False
    error_code: str
    error_message: str
    detail: Optional[str] = None


async def hegemony_error_handler(request: Request, exc: HegemonyError) -> JSONResponse:
    logger.warning(f"Hegemony Error [{exc.error_code}]: {exc.message}")
    return JSONResponse(
        status_code=getattr(exc, "status_code", 500),
        content=ErrorResponse(
            error_code=getattr(exc, "error_code", "INTERNAL_ERROR"),
            error_message=getattr(exc, "message", str(exc)),
            detail=str(getattr(exc, "original", None)) if getattr(exc, "original", None) else None,
        ).model_dump(),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            error_message="リクエストのバリデーションに失敗しました",
            detail=str(exc.errors()),
        ).model_dump(),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR", error_message="内部エラーが発生しました", detail=str(exc)
        ).model_dump(),
    )


def register_error_handlers(app: FastAPI) -> None:
    """FastAPIアプリにエラーハンドラを一括登録する"""
    app.add_exception_handler(HegemonyError, hegemony_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
