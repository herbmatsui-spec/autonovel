from fastapi import APIRouter, Depends

from src.backend.auth import require_api_key
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.models.api_schemas import BookSchema, BookCreateRequest, BookScoreHistoryResponse, PDCACycleSnapshot

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
    }


@router.post("", response_model=BookSchema)
@router.post("/", response_model=BookSchema)
async def create_book(payload: BookCreateRequest, api_key: str = Depends(require_api_key)):
    async with UnitOfWork(AppContainer.db()) as uow:
        book_id = await uow.books.create_book(
            title=payload.title,
            genre=payload.genre,
            concept=payload.concept,
            synopsis=payload.synopsis,
            target_eps=payload.target_eps,
            style_dna={},
            marketing_data={},
        )
        b = await uow.books.get_book(book_id)
    if not b:
        from src.core.exceptions import NotFoundError

        raise NotFoundError("Book not found after creation", resource_type="Book", resource_id=str(book_id))

    return {
        "id": b.id,
        "title": b.title,
        "genre": b.genre,
        "concept": b.concept,
        "synopsis": b.synopsis,
        "target_eps": b.target_eps,
        "cumulative_stress": b.cumulative_tension or 0.0,
        "created_at": b.created_at,
    }


@router.delete("/{book_id}")
async def delete_book(book_id: int, api_key: str = Depends(require_api_key)):
    async with UnitOfWork(AppContainer.db()) as uow:
        await uow.books.delete_book(book_id)
    return {"message": f"Book {book_id} deleted successfully"}


@router.get("/{book_id}/book-scores/history", response_model=BookScoreHistoryResponse)
async def get_book_score_history(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        book = await uow.books.get_book(book_id)
        if not book:
            from src.core.exceptions import NotFoundError
            raise NotFoundError("Book not found", resource_type="Book", resource_id=str(book_id))

        history = await uow.book_scores.get_history_for_book(book_id)
        all_benchmarks = await uow.book_scores.get_genre_benchmarks()
        genre_benchmark = all_benchmarks.get(book.genre)

    return {
        "success": True,
        "book_id": book_id,
        "history": [
            {
                "chapter_number": h.chapter_number,
                "overall_score": h.overall_score,
                "structure_score": h.structure_score,
                "coherency_score": h.coherency_score,
                "factual_grounding_score": h.factual_grounding_score,
                "visual_textual_synergy_score": h.visual_textual_synergy_score,
                "reader_experience_score": h.reader_experience_score,
                "evaluated_at": h.evaluated_at,
                "evaluator_version": h.evaluator_version,
            }
            for h in history
        ],
        "benchmarks": genre_benchmark,
    }


@router.get("/{book_id}/pdca/cycles/{chapter_number}", response_model=list[PDCACycleSnapshot])
async def get_pdca_cycles(book_id: int, chapter_number: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        snapshots = await uow.pdca_history.get_by_chapter(book_id, chapter_number)

    return [
        {
            "book_id": s.book_id,
            "chapter_number": s.chapter_number,
            "cycle_number": s.cycle_number,
            "initial_score": s.initial_score,
            "final_score": s.final_score,
            "score_delta": s.score_delta,
            "improved_percentage": s.improved_percentage,
            "lowest_dimension": s.lowest_dimension,
            "directives": s.directives,
            "history": s.history,
            "converged": s.converged,
            "created_at": s.created_at,
        }
        for s in snapshots
    ]
