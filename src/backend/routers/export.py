"""
routers/export.py - 出版フォーマット自動整形エクスポーター API

指定プラットフォーム（なろう/カクヨム/Nocturne）向けに小説本文を整形して出力する。
自動投稿ではなく、人間がコピペする用の整形済みテキストを提供する。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.backend.database.models import Book, Chapter
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.services.exporters.base import get_exporter, list_platforms

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/platforms")
async def get_platforms() -> list[dict[str, str]]:
    """対応プラットフォーム一覧を取得する。"""
    return list_platforms()


@router.get("/books/{book_id}")
async def export_book(
    book_id: int,
    platform: str = Query("narou", description="narou | kakuyomu | nocturn"),
) -> dict[str, Any]:
    """作品を指定プラットフォーム用に整形して出力する。"""
    from sqlalchemy import select

    async with UnitOfWork(AppContainer.db()) as uow:
        book = await uow.session.execute(select(Book).where(Book.id == book_id))
        book_row = book.scalar_one_or_none()
        if book_row is None:
            raise HTTPException(status_code=404, detail="Book not found")

        chapters_result = await uow.session.execute(
            select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.ep_num)
        )
        chapters = [
            {"ep_num": c.ep_num, "title": c.title, "content": c.content or ""}
            for c in chapters_result.scalars().all()
        ]

        novel = {
            "title": book_row.title,
            "synopsis": book_row.synopsis or book_row.concept or "",
            "is_adult": bool(getattr(book_row, "sanctuary_integrity", 100) < 100),
        }

    exporter = get_exporter(platform)
    text = exporter.export(novel, chapters)
    return {"platform": platform, "title": novel["title"], "content": text}
