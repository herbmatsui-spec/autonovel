"""writing_use_cases の正常系単体テスト"""
import pytest
from unittest.mock import AsyncMock
from src.application.use_cases.writing_use_cases import WriteEpisodeUseCase

@pytest.mark.asyncio
async def test_write_episode_use_case_initialization_and_types():
    mock_ep_repo = AsyncMock()
    mock_novel_repo = AsyncMock()
    mock_uow = AsyncMock()
    mock_writing_service = AsyncMock()

    use_case = WriteEpisodeUseCase(
        episode_repo=mock_ep_repo,
        novel_repo=mock_novel_repo,
        uow=mock_uow,
        writing_service=mock_writing_service,
    )
    assert use_case.writing_service is not None
