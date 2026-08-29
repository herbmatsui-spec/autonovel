from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.database.repositories.chapter import ChapterRepository


@pytest.mark.asyncio
async def test_chapter_create_calls_update_style_learned():
    # Create a repository instance with a mocked session
    mock_session = MagicMock()
    repo = ChapterRepository(mock_session)

    # Mock the result of select(Chapter).where(...) to return None (so a new Chapter is created)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    # Make execute an AsyncMock that returns mock_result
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock the Chapter class
    mock_chapter_class = MagicMock()
    mock_chapter_instance = MagicMock()
    mock_chapter_class.return_value = mock_chapter_instance

    # Mock the select function to return a mock select object that chains where
    mock_select = MagicMock()
    mock_select.where.return_value = mock_select  # allow chaining

    with patch('src.backend.database.repositories.chapter.Chapter', mock_chapter_class), \
         patch('src.backend.database.repositories.chapter.select', mock_select):
        # Also we need to mock the imports inside the try block: we want to see if update_style_learned is called
        with patch('src.services.style_learning.update_style_learned') as mock_update_style:
            # Call the method
            await repo.create_chapter(
                book_id=1,
                ep_num=1,
                title="Test",
                content="テスト本文。",
                summary="テスト要約。",
                killer_phrase=None,
                ai_insight="",
                world_state={},
                trinity_review_log={},
                created_at="2024-01-01",
                branch_id=1,
            )

            # Check that update_style_learned was called with the expected arguments
            mock_update_style.assert_called_once_with(1, 1, "テスト本文。", branch_id=1)
