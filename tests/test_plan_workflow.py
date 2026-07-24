import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.mocks.test_harness import BackendTestHarness
from src.backend.workflows.plan_generation_workflow import PlanGenerationWorkflow
from src.shared.utils import StatusReporter

@pytest.fixture
def harness():
    return BackendTestHarness()

@pytest.mark.asyncio
async def test_plan_generation_workflow_success(harness):
    """
    PlanGenerationWorkflow の正常系テスト:
    - planner.create_hegemony_plan が正しく呼ばれ、
    - book_id と title が正しく返されることを確認する。
    """
    params = {
        "genre": "異世界ファンタジー",
        "keywords": "無双, スローライフ",
        "style_key": "default",
        "concept": "最強の魔法使いが辺境で店を開く",
        "title": "辺境の魔法店",
        "cheat_scale": 5,
        "growth_curve": "最初から最強",
        "system_assist": 70,
        "cost_severity": 2,
        "target_eps": 100,
        "initial_limit": 15,
    }
    
    # Mock Bible
    mock_bible = MagicMock()
    mock_bible.title = "辺境の魔法店 (生成済み)"
    
    # Mock Planner
    mock_planner = AsyncMock()
    mock_planner.create_hegemony_plan.return_value = (123, mock_bible)
    
    # Workflow Instance
    workflow = PlanGenerationWorkflow()
    workflow.planner = mock_planner
    
    reporter = MagicMock(spec=StatusReporter)
    
    # Execution
    result = await workflow.execute(
        reporter=reporter,
        params=params
    )
    
    # Assertions
    assert result["book_id"] == 123
    assert result["title"] == "辺境の魔法店 (生成済み)"
    
    # Verify planner call arguments
    mock_planner.create_hegemony_plan.assert_called_once_with(
        genre=params["genre"],
        keywords=params["keywords"],
        style_key=params["style_key"],
        concept=params["concept"],
        title=params["title"],
        cheat_scale=params["cheat_scale"],
        growth_curve=params["growth_curve"],
        system_assist=params["system_assist"],
        cost_severity=params["cost_severity"],
        target_eps=params["target_eps"],
        initial_plot_limit=params["initial_limit"],
        reporter=reporter
    )

@pytest.mark.asyncio
async def test_plan_generation_workflow_default_params(harness):
    """
    パラメータが不足している場合にデフォルト値が使用されることを確認する。
    """
    params = {} # Empty params
    
    mock_bible = MagicMock()
    mock_bible.title = "デフォルトタイトル"
    
    mock_planner = AsyncMock()
    mock_planner.create_hegemony_plan.return_value = (456, mock_bible)
    
    workflow = PlanGenerationWorkflow()
    workflow.planner = mock_planner
    
    reporter = MagicMock(spec=StatusReporter)
    
    await workflow.execute(
        reporter=reporter,
        params=params
    )
    
    # Verify default values were passed to the planner
    args, kwargs = mock_planner.create_hegemony_plan.call_args
    assert kwargs["genre"] == "ファンタジー"
    assert kwargs["target_eps"] == 50
    assert kwargs["initial_plot_limit"] == 10
