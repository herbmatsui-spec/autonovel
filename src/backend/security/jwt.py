from datetime import datetime, timedelta, timezone
from typing import Any
import jwt

from src.backend.config import settings

def get_secret_key() -> str:
    """現在の環境に応じた安全なJWT秘密鍵を取得する。"""
    return settings.get_jwt_secret_key()

def create_access_token(
    data: dict | int | str | None = None,
    role: str | None = None,
    expires_delta: timedelta | None = None,
    *,
    user_id: int | str | None = None,
    **kwargs: Any,
) -> str:
    if isinstance(data, dict):
        sub = str(data.get("sub") or data.get("user_id") or user_id or "")
        token_role = data.get("role") or role or kwargs.get("role") or "user"
    else:
        sub = str(data or user_id or kwargs.get("user_id") or "")
        token_role = role or kwargs.get("role") or "user"

    to_encode = {"sub": sub, "role": token_role, "type": "access"}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: dict | int | str | None = None,
    *,
    user_id: int | str | None = None,
    **kwargs: Any,
) -> str:
    if isinstance(data, dict):
        sub = str(data.get("sub") or data.get("user_id") or user_id or "")
    else:
        sub = str(data or user_id or kwargs.get("user_id") or "")

    to_encode = {"sub": sub, "type": "refresh"}
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
