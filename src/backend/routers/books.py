from fastapi import APIRouter, HTTPException, Depends
from src.backend.engine_helpers import get_engine as resolve_engine
from src.backend.task_helpers import create_task as _create_create_task
from config.container import Container
from src.backend.database.uow import UnitOfWork
from src.models.api_schemas import BookSchema
from src.backend.auth import require_api_key

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/", response_model=list[BookSchema])
async def list_books():
    async with UnitOfWork(Container.db()) as uow:
        books = await uow.books.get_all_books()

    return [
        {
            "id": b.id,
            "title": b.title,
            "genre": b.genre,
            "concept": b.concept,
            "synopsis": b.synopsis,
            "target_eps": b.target_eps,
            "cumulative_stress": b.cumulative_tension,
            "created_at": b.created_at,
        }
        for b in books
    ]


@router.get("/{book_id}", response_model=BookSchema)
async def get_book(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
        b = await uow.books.get_book(book_id)
    if not b:
        from src.core.exceptions import NotFoundError

        raise NotFoundError("Book not found", resource_type="Book", resource_id=str(book_id))

    return {
        "id": b.id,
        "title": b.title,
        "genre": b.genre,
        "concept": b.concept,
        "synopsis": b.synopsis,
        "target_eps": b.target_eps,
        "cumulative_stress": b.cumulative_tension,
        "created_at": b.created_at,
    }


@router.delete("/{book_id}")
async def delete_book(book_id: int, api_key: str = Depends(require_api_key)):
    async with UnitOfWork(Container.db()) as uow:
        await uow.books.delete_book(book_id)
    return {"message": f"Book {book_id} deleted successfully"}
