# ruff: noqa: B008
from fastapi import APIRouter, Depends

from src.application.use_cases.book_use_cases import BookUseCases
from src.backend.database.uow import UnitOfWork
from src.backend.auth import get_current_user
from src.backend.database.models import User
from src.core.container import AppContainer
from src.models.api_schemas import (
    BookCreateRequest,
    BookSchema,
    BookScoreHistoryResponse,
    PDCACycleSnapshot,
)

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("", response_model=list[BookSchema])
@router.get("/", response_model=list[BookSchema])
async def list_books(current_user: User = Depends(get_current_user)):
    async with UnitOfWork(AppContainer.db()) as uow:
        use_cases = BookUseCases(uow=uow)
        return await use_cases.list_books(user_id=current_user.id)


@router.get("/{book_id}", response_model=BookSchema)
async def get_book(book_id: int, current_user: User = Depends(get_current_user)):
    async with UnitOfWork(AppContainer.db()) as uow:
        use_cases = BookUseCases(uow=uow)
        return await use_cases.get_book(book_id=book_id, current_user=current_user)


@router.post("", response_model=BookSchema)
@router.post("/", response_model=BookSchema)
async def create_book(payload: BookCreateRequest, current_user: User = Depends(get_current_user)):
    async with UnitOfWork(AppContainer.db()) as uow:
        use_cases = BookUseCases(uow=uow)
        return await use_cases.create_book(payload=payload, current_user=current_user)


@router.delete("/{book_id}")
async def delete_book(book_id: int, current_user: User = Depends(get_current_user)):
    async with UnitOfWork(AppContainer.db()) as uow:
        use_cases = BookUseCases(uow=uow)
        await use_cases.delete_book(book_id=book_id, current_user=current_user)
    return {"message": f"Book {book_id} deleted successfully"}


@router.get("/{book_id}/book-scores/history", response_model=BookScoreHistoryResponse)
async def get_book_score_history(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        use_cases = BookUseCases(uow=uow)
        return await use_cases.get_book_score_history(book_id=book_id)


@router.get("/{book_id}/pdca/cycles/{chapter_number}", response_model=list[PDCACycleSnapshot])
async def get_pdca_cycles(book_id: int, chapter_number: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        use_cases = BookUseCases(uow=uow)
        return await use_cases.get_pdca_cycles(book_id=book_id, chapter_number=chapter_number)
