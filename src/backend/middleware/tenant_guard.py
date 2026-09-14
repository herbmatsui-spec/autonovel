from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import Book, User


async def verify_book_ownership(
    book_id: int,
    current_user: User,
    db_or_uow: Any,
) -> Book:
    """書籍の所有権を検証し、未所持かつ非管理者の場合は403 Forbiddenを送出する。

    db_or_uow には AsyncSession または UnitOfWork インスタンスを渡すことが可能。
    """
    session = getattr(db_or_uow, "session", db_or_uow)

    book = None
    if hasattr(session, "get"):
        book = await session.get(Book, book_id)
    elif hasattr(session, "execute"):
        result = await session.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作品 (ID: {book_id}) が見つかりません",
        )

    # 所有者または管理者のみアクセス許可
    if book.user_id is not None and book.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この作品に対するアクセス権限がありません",
        )

    return book
