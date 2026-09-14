import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.bible import BibleRepository
from src.backend.database.models import Bible

@pytest.mark.asyncio
async def test_bible_repository_get_terms():
    mock_session = AsyncMock()
    mock_bible = Bible(
        id=1, 
        book_id=1, 
        settings="Test settings",
        revealed="Test revealed",
        version=1
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_bible
    mock_session.execute.return_value = mock_result
    
    repo = BibleRepository(mock_session)
    terms = await repo.get_latest_bible(1)
    assert terms is not None