"""
src/backend/error_handlers.py - FastAPI統一エラーハンドラ
"""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.backend.response_helpers import api_error
from src.core.exceptions import HegemonyError

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """統一エラーレスポンス"""

    success: bool = False
    error_code: str
    error_message: str
    detail: Optional[str] = None


def _to_dict(model: BaseModel) -> dict:
    """Pydantic v1 / v2 両対応のシリアライズヘルパー"""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


async def hegemony_error_handler(request: Request, exc: HegemonyError) -> JSONResponse:
    logger.warning(f"Hegemony Error [{exc.error_code}]: {exc.message}")
    return api_error(
        getattr(exc, "error_code", "INTERNAL_ERROR"),
        getattr(exc, "message", str(exc)),
        str(getattr(exc, "original", None)) if getattr(exc, "original", None) else None,
        getattr(exc, "status_code", 500)
    )

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(f"Validation Error: {exc.errors()}")
    return api_error("VALIDATION_ERROR", "リクエストのバリデーションに失敗しました", str(exc.errors()), 422)

async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return api_error("INTERNAL_ERROR", "内部エラーが発生しました", "内部エラーが発生しました。詳細はログを参照してください。", 500)

def register_error_handlers(app: FastAPI) -> None:
    """FastAPIアプリにエラーハンドラを一括登録する"""
    app.add_exception_handler(HegemonyError, hegemony_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
