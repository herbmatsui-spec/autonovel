from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from typing import Dict
import json

from src.backend.auth import require_api_key
from src.backend.database.uow import UnitOfWork
from src.backend.sse_manager import get_sse_manager
from src.core.container import AppContainer
from src.models.api_schemas import BookSchema

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("", response_model=list[BookSchema])
@router.get("/", response_model=list[BookSchema])
async def list_books():
    async with UnitOfWork(AppContainer.db()) as uow:
        books = await uow.books.get_all_books()

    return [
        {
            "id": b.id,
            "title": b.title,
            "genre": b.genre,
            "concept": b.concept,
            "synopsis": b.synopsis,
            "target_eps": b.target_eps,
            "cumulative_stress": b.cumulative_tension or 0.0,
            "created_at": b.created_at,
            "axis_lock_flags": b.axis_lock_flags or {},
        }
        for b in books
    ]


@router.get("/{book_id}", response_model=BookSchema)
async def get_book(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
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
        "cumulative_stress": b.cumulative_tension or 0.0,
        "created_at": b.created_at,
        "axis_lock_flags": b.axis_lock_flags or {},
    }


@router.delete("/{book_id}")
async def delete_book(book_id: int, api_key: str = Depends(require_api_key)):
    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.books.delete_book(book_id)
    return {"message": f"Book {book_id} deleted successfully"}


class AxisLockFlagsUpdate(BaseModel):
    axis_lock_flags: Dict[str, bool]


@router.patch("/{book_id}/axis-locks", response_model=BookSchema)
async def update_axis_locks(book_id: int, payload: AxisLockFlagsUpdate, api_key: str = Depends(require_api_key)):
    async with UnitOfWork(AppContainer.db()) as uow:
        b = await uow.books.get_book(book_id)
    if not b:
        from src.core.exceptions import NotFoundError

        raise NotFoundError("Book not found", resource_type="Book", resource_id=str(book_id))

    # Update the column via raw SQL (or ORM) – using session
    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.session.execute(
            "UPDATE books SET axis_lock_flags = :flags WHERE id = :bid",
            {"flags": json.dumps(payload.axis_lock_flags), "bid": book_id},
        )
        await uow.session.commit()
        # Refresh
        b = await uow.books.get_book(book_id)

    # Broadcast SSE event for lock changes
    try:
        sse = get_sse_manager()
        await sse.broadcast("axis_locks", {"book_id": book_id, "axis_lock_flags": payload.axis_lock_flags})
    except Exception as e:
        # Log but don't fail the request
        import logging
        logging.getLogger(__name__).warning(f"Failed to broadcast axis_locks SSE: {e}")

    return {
        "id": b.id,
        "title": b.title,
        "genre": b.genre,
        "concept": b.concept,
        "synopsis": b.synopsis,
        "target_eps": b.target_eps,
        "cumulative_stress": b.cumulative_tension or 0.0,
        "created_at": b.created_at,
        "axis_lock_flags": b.axis_lock_flags or {},
    }
