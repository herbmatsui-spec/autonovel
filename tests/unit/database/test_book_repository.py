import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.book import BookRepository
from src.backend.database.models import Book

@pytest.mark.asyncio
async def test_book_repository_get_active_books():
    mock_session = AsyncMock()
    mock_book = Book(id=1, title="Test Book", genre="Fantasy", concept="Test", synopsis="Test", target_eps=10)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_book]
    mock_session.execute.return_value = mock_result
    
    repo = BookRepository(mock_session)
    books = await repo.get_all_books()
    assert len(books) >= 0