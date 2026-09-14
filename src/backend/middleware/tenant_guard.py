from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database.models import Book, User

async def verify_book_ownership(book_id: int, current_user: User, db: AsyncSession) -> Book:
    book = await db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="作品が見つかりません")
    if book.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="この作品に対するアクセス権限がありません")
    return book
