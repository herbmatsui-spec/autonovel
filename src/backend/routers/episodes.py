from fastapi import APIRouter
from config.container import Container
from src.backend.database.uow import UnitOfWork

router = APIRouter(prefix="/api/episodes", tags=["episodes"])

@router.get("/chapters/{book_id}")
async def get_chapters(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
        chapters = await uow.chapters.get_all_non_anchor_chapters(book_id)
    return [
        {
            "ep_num": c.ep_num,
            "title": c.title,
            "content": c.content,
            "summary": c.summary,
            "created_at": c.created_at
        }
        for c in chapters
    ]
