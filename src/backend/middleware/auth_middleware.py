"""
src/backend/middleware/auth_middleware.py - グローバル認証ミドルウェア

公開パス（ヘルスチェック、メトリクス、認証エンドポイント、Webhook 等）を除き、
すべてのリクエストに対して JWT または API Key の検証を要求する。
未認証アクセスをデフォルトで拒絶（Default Deny）することで、
ルーター単位での認証設定漏れによる脆弱性を根本から排除する。
"""

from __future__ import annotations

import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.backend.config import settings
from src.backend.security.jwt import decode_token

logger = logging.getLogger(__name__)

# 公開許可パス（完全一致、末尾スラッシュ除去後）
PUBLIC_EXACT_PATHS: set[str] = {
    "",
    "/health",
    "/health/liveness",
    "/health/readiness",
    "/health/detail",
    "/metrics",
    "/api/health",
    "/api/health/liveness",
    "/api/health/readiness",
    "/api/health/detail",
    "/api/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/billing/plans",
    "/api/billing/webhook",
    "/favicon.ico",
}

# 公開許可パスプレフィックス（静的アセット等）
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/assets/",
    "/favicon",
    "/docs",
    "/redoc",
    "/api/stream",
)


class GlobalAuthMiddleware(BaseHTTPMiddleware):
    """
    アプリケーション全体へのアクセスを保護する認証ミドルウェア。
    - Whitelist パス、AUTH_DISABLED=True、CORS preflight (OPTIONS) はバイパス
    - Bearer JWT または API Key (Authorization / X-API-Key) を検証
    - 検証失敗時は 401 Unauthorized を返却
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        path = request.url.path
        normalized_path = path.rstrip("/")

        # 1. 開発/テスト用バイパス (AUTH_DISABLED=True またはテスト時の dependency_overrides)
        if settings.AUTH_DISABLED:
            return await call_next(request)

        app_obj = getattr(request, "app", None)
        if app_obj and hasattr(app_obj, "dependency_overrides"):
            from src.backend.auth import (
                get_current_user,
                require_admin_user_or_key,
                require_api_key,
            )

            overrides = app_obj.dependency_overrides
            if (
                get_current_user in overrides
                or require_api_key in overrides
                or require_admin_user_or_key in overrides
            ):
                return await call_next(request)

        # 2. CORS Preflight (OPTIONS) は通過
        if request.method == "OPTIONS":
            return await call_next(request)

        # 3. 公開ホワイトリスト判定 (完全一致 or プレフィックス一致)
        if normalized_path in PUBLIC_EXACT_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
            return await call_next(request)

        # 4. 認証ヘッダーの取得と検証
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")

        # 4a. API Key 検証 (X-API-Key または Authorization)
        allowed_keys_str = settings.ALLOWED_API_KEYS or ""
        allowed_keys = {k.strip() for k in allowed_keys_str.split(",") if k.strip()}

        if api_key_header and api_key_header in allowed_keys:
            return await call_next(request)

        # 4b. Authorization ヘッダー検証
        if auth_header:
            token = ""
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            else:
                token = auth_header.strip()

            # API Key として一致するか確認
            if token and token in allowed_keys:
                return await call_next(request)

            # JWT トークンとして検証
            if token:
                try:
                    payload = decode_token(token, expected_type="access")
                    if payload and payload.get("sub"):
                        return await call_next(request)
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "無効または期限切れのトークンです"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                except Exception as exc:
                    logger.debug("AuthMiddleware: Token decode failed: %s", exc)
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "無効または期限切れのトークンです"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        # 5. 未認証拒絶 (Default Deny)
        return JSONResponse(
            status_code=401,
            content={"detail": "認証が必要です"},
            headers={"WWW-Authenticate": "Bearer"},
        )
