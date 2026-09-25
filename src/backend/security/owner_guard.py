"""リソース所有権ガード (IDOR防止)。"""
from __future__ import annotations
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import select

from src.backend.database.models import Book, User
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.core.exceptions import NotFoundError


async def verify_book_ownership(
    book_id: int,
    current_user: User,
    uow: UnitOfWork | None = None,
) -> Book:
    """指定された book_id が current_user に帰属しているか検証する。
    管理者 (role == 'admin') はバイパス可能。
    """
    async def _check(session: Any) -> Book:
        stmt = select(Book).where(Book.id == book_id)
        result = await session.execute(stmt)
        book = result.scalar_one_or_none()
        if not book:
            raise NotFoundError(f"作品が見つかりません: {book_id}", resource_type="Book", resource_id=str(book_id))

        user_role = getattr(current_user, "role", "user")
        if book.user_id != current_user.id and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この作品に対するアクセス権限がありません",
            )
        return book

    if hasattr(uow, "session") and uow.session is not None:
        return await _check(uow.session)
    elif hasattr(uow, "get_session"):
        async with uow.get_session() as session:
            return await _check(session)
    elif hasattr(uow, "execute"):
        return await _check(uow)
    else:
        async with UnitOfWork(AppContainer.db()) as local_uow:
            return await _check(local_uow.session)
