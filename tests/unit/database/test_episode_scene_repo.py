import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.chapter import ChapterRepository
from src.backend.database.models import Chapter

@pytest.mark.asyncio
async def test_chapter_update_content():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    repo = ChapterRepository(mock_session)
    await repo.update_chapter_content(branch_id=1, ep_num=1, content="新しい本文（15文字）")

    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_chapter_create_new():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.add = MagicMock()

    repo = ChapterRepository(mock_session)
    await repo.create_chapter(
        book_id=1,
        ep_num=1,
        title="Chapter 1",
        content="First chapter content",
        summary="Summary 1",
        killer_phrase="Phrase",
        ai_insight="Insight",
        world_state={"weather": "sunny"},
        trinity_review_log={},
        created_at="2026-09-15T00:00:00",
        branch_id=1,
    )

    mock_session.add.assert_called_once()

@pytest.mark.asyncio
async def test_chapter_get():
    mock_session = AsyncMock()
    mock_chapter = Chapter(
        id=1,
        book_id=1,
        branch_id=1,
        ep_num=1,
        title="Chapter 1",
        content="Content 1",
        summary="Chapter 1 plain summary",
        world_state="{}",
        trinity_review_log="{}",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_chapter
    mock_session.execute.return_value = mock_result

    repo = ChapterRepository(mock_session)
    ch = await repo.get_chapter(branch_id=1, ep_num=1)
    assert ch is not None
    assert ch.title == "Chapter 1"

@pytest.mark.asyncio
async def test_chapter_get_none():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    repo = ChapterRepository(mock_session)
    ch = await repo.get_chapter(branch_id=1, ep_num=99)
    assert ch is None

@pytest.mark.asyncio
async def test_chapter_delete():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    repo = ChapterRepository(mock_session)
    await repo.delete_chapter(book_id_or_branch_id=1, ep_num=1)
    mock_session.execute.assert_awaited_once()
