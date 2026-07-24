import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.mocks.test_harness import BackendTestHarness
from src.backend.workflows.plot_expansion_workflow import PlotExpansionWorkflow
from src.shared.utils import StatusReporter

@pytest.fixture
def harness():
    return BackendTestHarness()

@pytest.mark.asyncio
async def test_plot_expansion_workflow_success(harness):
    """
    PlotExpansionWorkflow の正常系テスト:
    - Bibleの取得
    - Tensionの目標値決定
    - Plannerによるプロット展開
    - Tensionのバリデーション
    が正しく動作することを確認する。
    """
    book_id = 1
    gen_from = 1
    gen_to = 2
    
    # Mock Data Setup
    # Bible settings for arcs
    mock_bible = MagicMock()
    mock_bible.settings = '{"arcs": ["Arc 1"]}'
    harness.uow.get_latest_bible = AsyncMock(return_value=mock_bible)
    
    # Mock tension service
    mock_tension = AsyncMock()
    mock_tension.determine_target_tension = AsyncMock()
    mock_tension.validate_tension_deviation = AsyncMock(return_value=(True, 0.0))
    
    # Mock planner
    mock_planner = AsyncMock()
    # Return mock plot results: ep_num and tension (0-100 scale)
    mock_planner.expand_plots.return_value = [
        MagicMock(ep_num=1, tension=50),
        MagicMock(ep_num=2, tension=60)
    ]
    
    # Workflow Instance
    workflow = PlotExpansionWorkflow()
    workflow.repo = harness.uow
    workflow.tension = mock_tension
    workflow.planner = mock_planner
    
    # Execution
    reporter = MagicMock(spec=StatusReporter)
    result = await workflow.execute(
        reporter=reporter,
        book_id=book_id,
        gen_from=gen_from,
        gen_to=gen_to,
        mode="final"
    )
    
    # Assertions
    assert result["count"] == 2
    assert result["mode"] == "final"
    
    # Verify tension determination was called for each episode
    assert mock_tension.determine_target_tension.call_count == 2
    
    # Verify planner was called with correct range
    mock_planner.expand_plots.assert_called_once()
    args, kwargs = mock_planner.expand_plots.call_args
    assert args[0] == book_id
    assert args[1] == [1, 2]
    assert kwargs["force"] is False
    
    # Verify tension validation was called
    assert mock_tension.validate_tension_deviation.call_count == 2

@pytest.mark.asyncio
async def test_plot_expansion_workflow_tension_warning(harness):
    """
    Tensionが目標から逸脱した場合にreporterに警告が出ることを確認する。
    """
    book_id = 1
    gen_from = 1
    gen_to = 1
    
    mock_bible = MagicMock()
    mock_bible.settings = '{}'
    harness.uow.get_latest_bible = AsyncMock(return_value=mock_bible)
    
    mock_tension = AsyncMock()
    mock_tension.determine_target_tension = AsyncMock()
    # Return (False, deviation) to trigger warning
    mock_tension.validate_tension_deviation = AsyncMock(return_value=(False, 0.5))
    
    mock_planner = AsyncMock()
    mock_planner.expand_plots.return_value = [
        MagicMock(ep_num=1, tension=80)
    ]
    
    workflow = PlotExpansionWorkflow()
    workflow.repo = harness.uow
    workflow.tension = mock_tension
    workflow.planner = mock_planner
    
    # Mock reporter to capture logs
    reporter = MagicMock(spec=StatusReporter)
    
    await workflow.execute(
        reporter=reporter,
        book_id=book_id,
        gen_from=gen_from,
        gen_to=gen_to,
        mode="final"
    )
    
    # Verify that reporter.report was called with "warn"
    reporter.report.assert_called()
    call_args = reporter.report.call_args
    assert "逸脱しています" in call_args[0][0]
    assert call_args[0][1] == "warn"

@pytest.mark.asyncio
async def test_plot_expansion_workflow_candidates_mode(harness):
    """
    mode="candidates" の場合、plannerに force=True が渡され、バリデーションがスキップされることを確認する。
    """
    book_id = 1
    gen_from = 1
    gen_to = 1
    
    mock_bible = MagicMock()
    mock_bible.settings = '{}'
    harness.uow.get_latest_bible = AsyncMock(return_value=mock_bible)
    
    mock_tension = AsyncMock()
    mock_tension.determine_target_tension = AsyncMock()
    mock_tension.validate_tension_deviation = AsyncMock()
    
    mock_planner = AsyncMock()
    mock_planner.expand_plots.return_value = [
        MagicMock(ep_num=1, tension=50)
    ]
    
    workflow = PlotExpansionWorkflow()
    workflow.repo = harness.uow
    workflow.tension = mock_tension
    workflow.planner = mock_planner
    
    await workflow.execute(
        reporter=None,
        book_id=book_id,
        gen_from=gen_from,
        gen_to=gen_to,
        mode="candidates"
    )
    
    # Verify force=True was passed to planner
    args, kwargs = mock_planner.expand_plots.call_args
    assert kwargs["force"] is True
    
    # Verify tension validation was NOT called
    mock_tension.validate_tension_deviation.assert_not_called()
