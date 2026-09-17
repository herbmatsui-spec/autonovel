"""v5.0 統一ドメインスキーマ準拠の章（Chapter）ルーター。

Step 8: `src/models/api_schemas` から `src/domain/schemas` への移行と
レスポンスの正規化（ChapterSchema 統一）を担当する。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.auth import get_current_user
from src.backend.database.models import User
from src.backend.database.uow import UnitOfWork
from src.backend.security.owner_guard import verify_book_ownership
from src.core.container import AppContainer
from src.domain.schemas.chapter import ChapterSchema

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


@router.get("/books/{book_id}", response_model=list[ChapterSchema])
async def get_chapters(
    book_id: int, current_user: User = Depends(get_current_user)
) -> list[ChapterSchema]:
    """指定作品の全章を統一スキーマ ChapterSchema で正規化して返す。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await verify_book_ownership(book_id, current_user, uow)
        chapters = await uow.chapters.get_all_non_anchor_chapters(book_id)

    normalized: list[ChapterSchema] = []
    for ch in chapters:
        ep_num = getattr(ch, "ep_num", 0) or 0
        content = getattr(ch, "content", "") or ""
        summary = getattr(ch, "summary", "") or ""
        normalized.append(
            ChapterSchema(
                id=getattr(ch, "id", 0),
                book_id=book_id,
                episode_number=ep_num,
                title=getattr(ch, "title", "") or "",
                content=content,
                digest=(summary[:300] if summary else ""),
                word_count=len(content),
                status="completed" if content else "draft",
            )
        )
    return normalized
