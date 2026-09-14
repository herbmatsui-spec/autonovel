from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from fastapi import HTTPException, status

# 本番環境では環境変数から読み込むこと (SHA256用に32バイト以上)
SECRET_KEY = "autonovel-super-secret-key-32bytes-minimum-change-in-prod"
ALGORITHM = "HS256"

def create_access_token(user_id: int, role: str, expires_delta: timedelta | None = None) -> str:
    to_encode = {"sub": str(user_id), "role": role, "type": "access"}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    to_encode = {"sub": str(user_id), "type": "refresh"}
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="トークンの期限が切れています")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無効なトークンです")
