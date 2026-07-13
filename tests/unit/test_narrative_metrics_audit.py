from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.audit import LogicalAuditor


@pytest.mark.asyncio
async def test_score_narrative_metrics():
    # Setup
    mock_repo = MagicMock()
    mock_repo.get_latest_narrative_metrics = AsyncMock(return_value={"tension": 50, "emotional_satisfaction": 50, "mystery_density": 50})

    mock_pm = MagicMock()
    mock_pm.build_narrative_scoring_prompt = AsyncMock(return_value="Test Prompt")

    mock_generate_json = AsyncMock()
    mock_generate_json.return_value = {
        "metadata": {
            "pov_stability": 0.8,
            "empathy_gap": 0.3,
            "curiosity_hook_rate": 0.7,
            "sensory_density": 0.6,
            "catharsis_density": 0.9,
        }
    }

    auditor = LogicalAuditor(repo=mock_repo, pm=mock_pm, generate_json=mock_generate_json, ctx_mgr=MagicMock())

    result = await auditor.score_narrative_metrics(
        book_id=1,
        branch_id=1,
        ep_num=2,
        scene_num=1,
        scene_content="Test content",
        context="Test context"
    )

    assert isinstance(result, list)
    assert len(result) == 6
    names = {m["metric_name"]: m["score"] for m in result}
    assert names["pov_stability"] == 0.8
    assert names["empathy_gap"] == 0.3
    assert names["curiosity_hook_rate"] == 0.7
    assert names["sensory_density"] == 0.6
    assert names["catharsis_density"] == 0.9
    mock_generate_json.assert_called_once()
