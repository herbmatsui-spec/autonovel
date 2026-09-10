"""
Commercial publishing helper functions to be shared between routers and tasks.
"""
from typing import Any
from sqlalchemy import select
from src.backend.database.models import Book, Chapter
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer

async def _get_novel_data(book_id: int) -> dict[str, Any]:
    """書籍から小説の基本情報を取得する"""
    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        result = await uow.session.execute(select(Book).where(Book.id == book_id))
        book_row = result.scalar_one_or_none()
        if book_row is None:
            raise ValueError(f"Book {book_id} not found")
        
        return {
            "title": book_row.title,
            "synopsis": book_row.synopsis or book_row.concept or "",
            "genre": getattr(book_row, "genre", "general"),
            "tags": getattr(book_row, "tags", []),
            "is_adult": bool(getattr(book_row, "sanctuary_integrity", 100) < 100),
        }

async def _get_episodes_data(book_id: int, episode_ids: list[int] | None = None) -> list[dict[str, Any]]:
    """書籍からエピソードデータを取得する"""
    async with UnitOfWork(AppContainer.db()) as uow:
        chapters_query = (
            select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.ep_num)
        )
        if episode_ids:
            chapters_query = chapters_query.where(Chapter.id.in_(episode_ids))
        
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        chapters_result = await uow.session.execute(chapters_query)
        chapters = chapters_result.scalars().all()
        
        episodes_data = []
        for ch in chapters:
            episodes_data.append({
                "ep_num": ch.ep_num,
                "title": ch.title,
                "content": ch.content or "",
                "summary": getattr(ch, "summary", ""),
                # 投稿IDなどは呼び出し側でプラットフォームに応じて処理するため、ここでは基本情報のみ
            })
        return episodes_data
