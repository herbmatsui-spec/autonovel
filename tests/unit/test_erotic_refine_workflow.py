"""
tests/unit/test_erotic_refine_workflow.py
refine_erotic_workflowのユニットテスト（モック環境）。
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.backend.workflows.refine_erotic_workflow import RefineEroticWorkflow


@pytest.mark.asyncio
async def test_refine_erotic_workflow_success():
    """正常なケースのテスト"""
    mock_repo = MagicMock()
    mock_uow = MagicMock()
    mock_repo.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_repo.__aexit__ = AsyncMock(return_value=None)

    mock_chapter = MagicMock()
    mock_chapter.content = "元のコンテンツ"
    mock_plot = MagicMock()

    mock_uow.chapters.get_chapter = AsyncMock(return_value=mock_chapter)
    mock_uow.plots.get_plot = AsyncMock(return_value=mock_plot)
    mock_uow.session.commit = AsyncMock()

    workflow = RefineEroticWorkflow(repo=mock_repo)

    result = await workflow.execute(
        reporter=None,
        book_id=1,
        ep_num=1,
        intensity=2,
        platform_preset="kakuyomu_romance",
    )

    assert result["success"] is True
    assert result["intensity_applied"] == 2
    mock_uow.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refine_erotic_workflow_not_found():
    """チャプターが見つからない場合のテスト"""
    mock_repo = MagicMock()
    mock_uow = MagicMock()
    mock_repo.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_repo.__aexit__ = AsyncMock(return_value=None)

    mock_uow.chapters.get_chapter = AsyncMock(return_value=None)

    workflow = RefineEroticWorkflow(repo=mock_repo)

    with pytest.raises(ValueError, match="Chapter not found"):
        await workflow.execute(
            reporter=None,
            book_id=1,
            ep_num=99,
            intensity=2,
        )
