"""v5.0 統一ドメインスキーマ準拠のプロジェクト（Project）ルーター。

Step 9: `src/models/api_schemas` から `src/domain/schemas` への移行と
レスポンスの ProjectSchema 統一を担当する。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.backend.auth import get_current_user
from src.backend.database.models import User
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.domain.schemas.project import BookSchema, ProjectSchema

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _book_to_schema(book) -> BookSchema:
    """DBのBookレコードを統一 BookSchema に正規化する。"""
    return BookSchema(
        id=getattr(book, "id", 0),
        project_id=getattr(book, "user_id", 0) or 0,
        title=getattr(book, "title", "") or "",
        genre=getattr(book, "genre", "") or "fantasy",
        synopsis=getattr(book, "synopsis", "") or "",
        total_words=0,
        target_chapters=getattr(book, "target_eps", 20) or 20,
    )


@router.get("", response_model=list[ProjectSchema])
@router.get("/", response_model=list[ProjectSchema])
async def list_projects(current_user: User = Depends(get_current_user)) -> list[ProjectSchema]:
    """ユーザー所有の作品群を ProjectSchema（統一ドメインモデル）で返す。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        books = await uow.books.get_by_user(user_id=current_user.id)
    return [ProjectSchema(id=b.id, name=b.title, books=[_book_to_schema(b)]) for b in books]
