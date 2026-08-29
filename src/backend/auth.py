"""
src/backend/auth.py — API 認証ユーティリティ

api_key の検証ロジックを提供する。現在はシンプルな許可リスト方式を採用し、
将来的に JWT/OAuth 等へ置き換え可能な抽象化レイヤーとする。
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import List, Optional, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed; skip environment file loading
    pass

try:
    from fastapi import HTTPException, Request
except ImportError:
    # FastAPI not installed in test environment; provide minimal stand‑ins
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: Any = None):
            self.status_code = status_code
            self.detail = detail
    class Request:  # dummy request placeholder for typing
        pass

from src.core.exceptions import AppError

logger = logging.getLogger(__name__)


class APIKeyService:
    """API キーの検証を司るサービス。"""

    def __init__(self, allowed_keys: Optional[List[str]] = None, disabled: Optional[bool] = None):
        self.allowed_keys = allowed_keys or []
        self._disabled = disabled

    @property
    def disabled(self) -> bool:
        if self._disabled is not None:
            return self._disabled
        return os.environ.get("AUTH_DISABLED", "false").lower() in ("1", "true", "yes")

    def validate(self, api_key: str) -> bool:
        # Check if authentication is disabled via AUTH_DISABLED
        disabled_env = os.getenv("AUTH_DISABLED", "false").lower() in ("1", "true", "yes")
        env = os.getenv("ENVIRONMENT", "development")
        if disabled_env:
            if env == "production":
                logger.error(
                    "AUTH_DISABLED is set but ENVIRONMENT=production - authentication is required"
                )
                return False
            logger.warning("AUTH_DISABLED is set - authentication is bypassed (non-production)")
            return True
        
        # If allowed_keys list is provided, check membership
        if self.allowed_keys:
            # Development bypass for convenience
            if os.getenv("API_KEY_DEV_BYPASS", "false").lower() == "true":
                return True
            return api_key in self.allowed_keys
        # No allowed keys configured – fail closed
        return False

    def get_rate_limit_key(self, api_key: str) -> str:
        """API key ベースのレート制限キーを返す。
        完全ハッシュ（SHA‑256）を使用し、キー衝突リスクを排除します。
        既存コードとの互換性のため、ハッシュ全体を返すが、過去キーとのマイグレーションはテストでシミュレートします。
        """
        import hashlib
        # SHA‑256 の十六進文字列全体を利用（長さ 64）
        full_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        return f"apikey:{full_hash}"


_api_key_service: Optional[APIKeyService] = None


def reset_api_key_service() -> None:
    """テスト時や環境変数変更時に APIKeyService シングルトンをリセットする"""
    global _api_key_service
    _api_key_service = None


def get_api_key_service() -> APIKeyService:

    global _api_key_service
    if _api_key_service is None:
        disabled_env = os.environ.get("AUTH_DISABLED", "false").lower() in ("1", "true", "yes")
        env = os.environ.get("ENVIRONMENT", "development")
        if disabled_env and env == "production":
            raise RuntimeError(
                "起動時エラー: AUTH_DISABLED が設定されていますが、ENVIRONMENT=production では認証をバイパスできません。"
                "本番環境では認証が無効化された状態での起動は許可されません。"
            )
        keys_env = os.environ.get("ALLOWED_API_KEYS", "")
        allowed_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        
        # Warn if no API keys are configured and we're not using bypass mechanisms
        if not allowed_keys and not disabled_env:
            dev_bypass = os.getenv("API_KEY_DEV_BYPASS", "false").lower() == "true"
            if not dev_bypass:
                logger.warning(
                    "ALLOWED_API_KEYS environment variable is not set or empty. "
                    "API key authentication is enabled but no keys are configured. "
                    "All API key validation attempts will fail. "
                    "For development, set API_KEY_DEV_BYPASS=true or configure explicit API keys."
                )
        
        _api_key_service = APIKeyService(allowed_keys=allowed_keys, disabled=disabled_env if "AUTH_DISABLED" in os.environ else None)
    return _api_key_service


async def require_api_key(request: Request) -> str:

    service = get_api_key_service()
    api_key = request.headers.get("X-API-Key")
    if service.disabled:
        return api_key or "dev-disabled-key"
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "UNAUTHORIZED",
                "error_message": "API キーが指定されていません。X-API-Key ヘッダーを設定してください。",
            },
        )
    if not service.validate(api_key):
        logger.warning(
            f"Invalid API key attempt from "
            f"{request.client.host if request.client else 'unknown'} "
            f"key_prefix={api_key[:4]}***"
        )
        raise HTTPException(
            status_code=403,
            detail={"error_code": "FORBIDDEN", "error_message": "API キーが無効です。"},
        )
    return api_key


def validate_api_key_or_raise(api_key: str) -> str:
    service = get_api_key_service()
    if service.disabled:
        return api_key or "dev-disabled-key"
    if not service.validate(api_key):
        raise AppError("API キーが無効です。", status_code=403, error_code="FORBIDDEN")
    return api_key
