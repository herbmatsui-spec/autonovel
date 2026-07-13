from unittest.mock import AsyncMock

import pytest

from src.backend.database.models import Plot
from src.backend.engine import UltimateHegemonyEngine
from src.backend.workflows.plot_expansion_workflow import PlotExpansionWorkflow
from tests.mocks.mock_llm import MockGeminiApiClient as MockLLM


class MockStatusReporter:
    def __init__(self):
        self.reports = []
    def report(self, message, level="info"):
        self.reports.append({"message": message, "level": level})

@pytest.mark.asyncio
async def test_tension_integration_workflow():
    # 1. Setup mocks
    mock_llm = MockLLM()
    # LLMが返すプロットエピソードの形式を模倣
    mock_llm.add_json_response(".*", {
        "episodes": [
            {
                "ep_num": 1,
                "tension": 0.8, # 目標からわざと逸脱させる (targetは通常 0.1-0.3 程度)
                "summary": "Test plot episode 1",
                "detailed_blueprint": "Detailed blueprint 1"
            }
        ]
    })

    # Mock Repository
    # Mock Repository
    mock_repo = AsyncMock()
    # get_total_episodes を 10 に設定
    mock_repo.get_total_episodes.return_value = 10
    # get_plot は target_tension を持つモデルを返す
    mock_plot_model = AsyncMock(spec=Plot)
    mock_plot_model.target_tension = 0.2
    mock_repo.get_plot.return_value = mock_plot_model

    # Engine setup
    engine = AsyncMock(spec=UltimateHegemonyEngine)
    engine.repo = mock_repo
    engine.ai_api = mock_llm
    engine.determine_target_tension = UltimateHegemonyEngine.determine_target_tension.__get__(engine, UltimateHegemonyEngine)
    engine.validate_tension_deviation = UltimateHegemonyEngine.validate_tension_deviation.__get__(engine, UltimateHegemonyEngine)

    # Workflow setup
    workflow = PlotExpansionWorkflow(engine=engine)
    reporter = MockStatusReporter()

    # 2. Execute workflow
    # 1話分だけ生成させる
    kwargs = {
        "book_id": 1,
        "gen_from": 1,
        "gen_to": 1,
        "genre": "Fantasy",
        "story_type": "standard"
    }

    await workflow.execute(reporter, **kwargs)

    # 3. Assertions
    # 目標 tension の決定が呼ばれたか
    mock_repo.update_plot_target_tension.assert_called()

    # tension 逸脱の警告が出ているか (0.2 target vs 0.8 generated)
    tension_warnings = [r for r in reporter.reports if "Tensionが目標から逸脱" in r["message"]]
    assert len(tension_warnings) > 0, "Tension deviation warning should be reported"
    assert tension_warnings[0]["level"] == "warn"

@pytest.mark.asyncio
async def test_tension_integration_success():
    # 正常系: tensionが目標範囲内である場合
    mock_llm = MockLLM()
    mock_llm.add_json_response(".*", {
        "episodes": [
            {
                "ep_num": 1,
                "tension": 0.25, # 0.2 target に対して許容範囲内 (tolerance=0.2)
                "summary": "Test plot episode 1",
                "detailed_blueprint": "Detailed blueprint 1"
            }
        ]
    })

    mock_repo = AsyncMock()
    mock_repo.get_total_episodes.return_value = 10
    mock_plot_model = AsyncMock(spec=Plot)
    mock_plot_model.target_tension = 0.2
    mock_repo.get_plot.return_value = mock_plot_model

    engine = AsyncMock(spec=UltimateHegemonyEngine)
    engine.repo = mock_repo
    engine.ai_api = mock_llm
    engine.determine_target_tension = UltimateHegemonyEngine.determine_target_tension.__get__(engine, UltimateHegemonyEngine)
    engine.validate_tension_deviation = UltimateHegemonyEngine.validate_tension_deviation.__get__(engine, UltimateHegemonyEngine)
    workflow = PlotExpansionWorkflow(engine=engine)
    reporter = MockStatusReporter()

    await workflow.execute(reporter, **{"book_id": 1, "gen_from": 1, "gen_to": 1, "genre": "Fantasy", "story_type": "standard"})

    # 警告が出ていないことを確認
    tension_warnings = [r for r in reporter.reports if "Tensionが目標から逸脱" in r["message"]]
    assert len(tension_warnings) == 0, "Tension deviation warning should NOT be reported for valid values"
