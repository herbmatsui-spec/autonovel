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

async def _get_episodes_data(
    book_id: int, episode_ids: list[int] | None = None, platforms: list[str] | None = None
) -> list[dict[str, Any]]:
    """書籍からエピソードデータを取得する（プラットフォーム投稿ID含む）"""
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
        
        platforms_list = platforms or []
        episodes_data = []
        for ch in chapters:
            ep_info = {
                "id": ch.id,
                "ep_num": ch.ep_num,
                "title": ch.title,
                "content": ch.content or "",
                "summary": getattr(ch, "summary", ""),
            }
            for p in platforms_list:
                ep_info[f"{p}_post_id"] = getattr(ch, f"{p}_post_id", None)
                ep_info[f"{p}_post_url"] = getattr(ch, f"{p}_post_url", None)
            episodes_data.append(ep_info)
        return episodes_data
