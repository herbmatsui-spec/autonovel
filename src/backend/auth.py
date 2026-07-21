"""
src/backend/auth.py — API 認証ユーティリティ

api_key の検証逻辑を提供する。現在はシンプルな許可リスト方式を採用し、
将来的に JWT/OAuth 等へ置き換え可能な抽象化レイヤーとする。
"""
from __future__ import annotations

import os
import logging
from typing import List, Optional

from fastapi import Request, HTTPException
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


class APIKeyService:
    """API キーの検証を司るサービス。"""

    def __init__(self, allowed_keys: Optional[List[str]] = None, disabled: bool = False):
        self.allowed_keys = allowed_keys or []
        self.disabled = disabled

    def validate(self, api_key: str) -> bool:
        if self.disabled:
            return True
        if not self.allowed_keys:
            return True
        return api_key in self.allowed_keys


_api_key_service: Optional[APIKeyService] = None


def get_api_key_service() -> APIKeyService:
    global _api_key_service
    if _api_key_service is None:
        disabled = os.environ.get("AUTH_DISABLED", "false").lower() in ("1", "true", "yes")
        keys_env = os.environ.get("ALLOWED_API_KEYS", "")
        allowed_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        _api_key_service = APIKeyService(allowed_keys=allowed_keys, disabled=disabled)
    return _api_key_service


async def require_api_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={"error_code": "UNAUTHORIZED", "error_message": "API キーが指定されていません。X-API-Key ヘッダーを設定してください。"},
        )
    service = get_api_key_service()
    if not service.validate(api_key):
        logger.warning(f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=403,
            detail={"error_code": "FORBIDDEN", "error_message": "API キーが無効です。"},
        )
    return api_key


def validate_api_key_or_raise(api_key: str) -> str:
    service = get_api_key_service()
    if not service.validate(api_key):
        raise AppError("API キーが無効です。", status_code=403, error_code="FORBIDDEN")
    return api_key
