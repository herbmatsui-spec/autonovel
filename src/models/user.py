from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

try:
    from pydantic import EmailStr
    from pydantic import create_model
    create_model("_TestEmailValidator", email=(EmailStr, ...))
except Exception:
    EmailStr = str  # type: ignore[misc,assignment]

class UserRole(str, Enum):
    USER = "user"
    PRO = "pro"
    ADMIN = "admin"

class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"

class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., min_length=8, max_length=128, description="パスワード")
    display_name: str = Field(..., min_length=1, max_length=50, description="作家名/表示名")

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserProfileResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: UserRole
    status: UserStatus
    credits: int
    plan_tier: str
    created_at: datetime
