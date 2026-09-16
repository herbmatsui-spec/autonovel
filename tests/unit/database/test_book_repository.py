import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.book import BookRepository
from src.backend.database.models import Book

@pytest.mark.asyncio
async def test_book_repository_get_active_books():
    mock_session = AsyncMock()
    mock_book = Book(
        id=1,
        user_id=1,
        title="Test Book",
        genre="Fantasy",
        concept="Test Concept",
        synopsis="Test Synopsis",
        target_eps=10,
        style_dna="{}",
        marketing_data="{}",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_book]
    mock_session.execute.return_value = mock_result

    repo = BookRepository(mock_session)
    books = await repo.get_all_books()
    assert len(books) == 1
    assert books[0].title == "Test Book"

@pytest.mark.asyncio
async def test_book_repository_create_book():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    repo = BookRepository(mock_session)
    await repo.create_book(
        user_id=1,
        title="New Novel",
        genre="Sci-Fi",
        concept="AI takeover",
        synopsis="A story of AI",
        target_eps=20,
        style_dna={"tone": "dark"},
        marketing_data={"tags": ["AI"]},
    )

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()

@pytest.mark.asyncio
async def test_book_repository_get_book():
    mock_session = AsyncMock()
    mock_book = Book(
        id=42,
        user_id=1,
        title="Specific Book",
        genre="Fantasy",
        concept="Hero",
        synopsis="Journey",
        target_eps=15,
        style_dna="{}",
        marketing_data="{}",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_book
    mock_session.execute.return_value = mock_result

    repo = BookRepository(mock_session)
    book = await repo.get_book(42, user_id=1)
    assert book is not None
    assert book.id == 42
    assert book.title == "Specific Book"

@pytest.mark.asyncio
async def test_book_repository_get_book_not_found():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    repo = BookRepository(mock_session)
    book = await repo.get_book(999)
    assert book is None

@pytest.mark.asyncio
async def test_book_repository_updates():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    repo = BookRepository(mock_session)
    await repo.update_book_cumulative_tension(book_id=1, user_id=1, tension=75)
    await repo.update_book_cumulative_stress(book_id=1, user_id=1, stress=50)
    await repo.update_book_target_eps(book_id=1, user_id=1, new_total_eps=30)
    await repo.delete_book(book_id=1, user_id=1)

    assert mock_session.execute.await_count == 4
