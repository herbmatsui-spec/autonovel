from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from fastapi import HTTPException, status

from src.backend.config import settings

def get_secret_key() -> str:
    """現在の環境に応じた安全なJWT秘密鍵を取得する。"""
    return settings.get_jwt_secret_key()

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = {"sub": str(data.get("sub")), "role": data.get("role"), "type": "access"}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = {"sub": str(data.get("sub")), "type": "refresh"}
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[settings.JWT_ALGORITHM])
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload
    except Exception:
        return None
