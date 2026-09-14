import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.chapter import ChapterRepository

@pytest.mark.asyncio
async def test_chapter_update_content():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    
    repo = ChapterRepository(mock_session)
    await repo.update_chapter_content(branch_id=1, ep_num=1, content="新しい本文（15文字）")
    
    mock_session.execute.assert_awaited_once()