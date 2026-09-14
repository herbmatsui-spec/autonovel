"""
src/backend/auth.py — API 認証ユーティリティ
"""

from __future__ import annotations

import logging
import os

from fastapi import Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database import get_db
from src.backend.database.models import User
from src.backend.security.jwt import decode_token
from fastapi.security import OAuth2PasswordBearer
from src.dependencies import get_prompt_manager

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="認証が必要です")
    payload = decode_token(token)
    user_id = int(payload["sub"]) if isinstance(payload["sub"], (int, str)) and str(payload["sub"]).isdigit() else payload["sub"]
    user = await db.get(User, user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ユーザーが無効です")
    return user

async def require_api_key(authorization: str = Header(default="", alias="Authorization")) -> str:
    """APIキーの簡易検証を行う依存性関数"""
    allowed_keys_str = os.environ.get("ALLOWED_API_KEYS", "")
    allowed_keys = [k.strip() for k in allowed_keys_str.split(",") if k.strip()]
    
    if not allowed_keys or os.environ.get("APP_ENV") == "development":
        return "dev-key"

    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    elif authorization:
        token = authorization

    if token in allowed_keys:
        return token
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key"
    )

async def validate_api_key_or_raise(authorization: str = Header(default="", alias="Authorization")) -> str:
    return await require_api_key(authorization)

__all__ = [
    "get_current_user",
    "require_api_key",
    "validate_api_key_or_raise",
    "get_prompt_manager",
    "oauth2_scheme",
]
