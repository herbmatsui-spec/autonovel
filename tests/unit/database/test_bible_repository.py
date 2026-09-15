import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.bible import BibleRepository
from src.backend.database.models import Bible

@pytest.mark.asyncio
async def test_bible_repository_create_and_get_latest():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    
    repo = BibleRepository(mock_session)
    await repo.create_bible(
        book_id=1,
        settings={"world": "cyberpunk"},
        version=1,
        last_updated="2026-09-15T00:00:00",
    )
    mock_session.add.assert_called_once()
    
    # Mock fetching latest
    mock_bible = Bible(
        id=1, 
        book_id=1, 
        settings="{\"world\": \"cyberpunk\"}",
        revealed="None",
        version=1
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_bible
    mock_session.execute.return_value = mock_result
    
    fetched = await repo.get_latest_bible(1)
    assert fetched is not None
    assert fetched.version == 1

@pytest.mark.asyncio
async def test_bible_repository_get_latest_none():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    repo = BibleRepository(mock_session)
    fetched = await repo.get_latest_bible(999)
    assert fetched is None