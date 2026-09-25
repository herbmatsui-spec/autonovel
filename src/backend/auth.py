"""
src/backend/auth.py — API 認証・認可ユーティリティ
"""

from __future__ import annotations

import logging
import os

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.backend.database import get_async_db, get_db
from src.backend.database.models import User
from src.backend.security.jwt import decode_token

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _get_dev_mock_user() -> User:
    """開発・テスト用のモック管理者ユーザーを生成する。"""
    user = User(
        id=1,
        email="dev@autonovel.local",
        display_name="Dev Admin",
        role="admin",
        status="active",
        plan_tier="enterprise",
        credits=99999,
    )
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """現在の認証済みユーザーを取得する。
    AUTH_DISABLED が True の場合は、開発用モックユーザーを返却してバイパスする。
    """
    if settings.AUTH_DISABLED:
        return _get_dev_mock_user()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンペイロードです",
        )

    user_id = int(sub) if isinstance(sub, (int, str)) and str(sub).isdigit() else sub
    user = await db.get(User, user_id)
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが存在しないか、無効化されています",
        )
    return user


async def require_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """管理者ロール（admin）を必須とする認可依存性。"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )
    return current_user


async def require_api_key(
    authorization: str = Header(default="", alias="Authorization"),
) -> str:
    """APIキーの検証を行う依存性関数。
    AUTH_DISABLED が True の場合のみ開発キーを許可し、それ以外は厳格に検証する。
    """
    if settings.AUTH_DISABLED:
        return "dev-key"

    # Extract token from header
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif authorization:
        token = authorization.strip()

    # Validate the extracted token
    result = validate_api_key_sync(token)
    if result is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return result  # token string


async def require_admin_user_or_key(
    token: str = Depends(oauth2_scheme),
    authorization: str = Header(default="", alias="Authorization"),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """管理者JWTまたは有効なAPI Keyのいずれかを要求する依存性関数。"""
    if settings.AUTH_DISABLED:
        return _get_dev_mock_user()

    if token:
        user = await get_current_user(token=token, db=db)
        if user.role == "admin":
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )

    # API Key を試行
    key = await require_api_key(authorization)
    if key:
        # API Key 保持者には読み取り専用ロールを付与（admin 昇格しない）
        api_user = _get_dev_mock_user()
        api_user.role = "api_readonly"
        return api_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="管理者認証または有効なAPI Keyが必要です",
    )


def validate_api_key_sync(api_key: str) -> str | bool:
    """同期コンテキスト用のAPIキー検証ヘルパー（タイミング攻撃耐性版）"""
    if settings.AUTH_DISABLED:
        return "dev-key"
    if not api_key:
        return False
    allowed_keys_str = getattr(settings, "ALLOWED_API_KEYS", "") or os.environ.get("ALLOWED_API_KEYS", "")
    allowed_keys = [k.strip() for k in allowed_keys_str.split(",") if k.strip()]
    if not allowed_keys:
        return False
    import hmac
    is_valid = any(hmac.compare_digest(api_key, k) for k in allowed_keys)
    if not is_valid:
        return False
    return api_key


async def validate_api_key_or_raise(
    authorization: str = Header(default="", alias="Authorization"),
) -> str:
    return await require_api_key(authorization)


def get_prompt_manager() -> Any:
    """FastAPI Depends 用の PromptManager プロバイダ。

    ``prompts.manager.PromptManager`` を遅延 import して返す。
    import 失敗時は None を返し、依存側でフォールバックできるようにする。
    """
    try:
        from prompts.manager import PromptManager

        return PromptManager()
    except Exception as e:  # noqa: BLE001
        logger.warning("PromptManager initialization failed: %s", e)
        return None


__all__ = [
    "get_current_user",
    "get_prompt_manager",
    "oauth2_scheme",
    "require_admin_user",
    "require_admin_user_or_key",
    "require_api_key",
    "validate_api_key_or_raise",
    "validate_api_key_sync",
]
