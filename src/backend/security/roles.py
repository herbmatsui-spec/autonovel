"""ロールベースアクセス制御 (RBAC) ガード。"""
from __future__ import annotations
from enum import Enum
from typing import Callable
from fastapi import Depends, HTTPException, status

from src.backend.auth import get_current_user
from src.backend.database.models import User


class UserRole(str, Enum):
    ADMIN = "admin"
    PRO = "pro"
    FREE = "free"
    USER = "user"


class RoleChecker:
    """指定されたロールのいずれかを保持しているか検証する依存性クラス。"""

    def __init__(self, allowed_roles: list[str | UserRole]):
        self.allowed_roles = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_role = getattr(current_user, "role", "user") or "user"
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"権限が不足しています。要求ロール: {self.allowed_roles}, ユーザーロール: {user_role}",
            )
        return current_user


def require_role(role: str | UserRole) -> Callable:
    """単一ロールを要求する依存関数ショートカット。"""
    return RoleChecker([role])


def require_admin() -> Callable:
    """Admin権限を要求する依存関数ショートカット。"""
    return RoleChecker([UserRole.ADMIN])
