# tests/integration/test_audit_aggregator_pipeline.py
"""Integration tests for AuditAggregator pipeline integration."""
import pytest
from unittest.mock import MagicMock

from src.agents.orchestrator import AgentContext, AgentName, AgentResult
from src.agents.specialists.adapter import AuditAggregatorNode
from src.backend.tasks.generation_tasks import _generate_orchestrated


@pytest.mark.asyncio
async def test_audit_aggregator_pipeline_integration():
    """Verify that AuditAggregator runs all 8 specialists and produces valid audit artifacts."""
    mock_session = MagicMock()
    mock_repo = MagicMock()
    mock_repo.session = mock_session

    node = AuditAggregatorNode(repo=mock_repo)
    ctx = AgentContext(
        book_id=10,
        branch_id=1,
        ep_num=2,
        artifacts={
            "drafted_text": (
                "王都の石畳を歩くアレンの前に、突如として黒装束の暗殺者が立ち塞がった。"
                "「ここで死んでもらう」と暗殺者が呟いたが、アレンは剣を抜き構えた。"
            ),
            "world_bible_snapshot": {
                "characters": [{"name": "アレン"}, {"name": "暗殺者"}],
                "locations": ["王都"],
            },
            "genre": "fantasy",
            "phase": "writing",
            "session": mock_session,
        },
    )

    result = await node(ctx)

    # 1. Next agent must be ILLUSTRATION
    assert result.next_agent == AgentName.ILLUSTRATION
    assert result.error is None

    # 2. Audit report must contain all 8 specialists
    report = result.artifacts.get("audit_report", {})
    assert "overall" in report
    assert 0.0 <= report["overall"] <= 100.0

    by_spec = report.get("by_specialist", {})
    assert len(by_spec) == 8
    for expected_name in [
        "consistency",
        "creativity",
        "reader_hook",
        "emotion_curve",
        "style",
        "factual",
        "structure",
        "multimodal",
    ]:
        assert expected_name in by_spec
        assert 0.0 <= by_spec[expected_name] <= 100.0

    # 3. Lowest dimension must be identified
    assert result.artifacts.get("lowest_dimension") in by_spec

    # 4. DB session execute must have been called for persistence
    assert mock_session.execute.called
    assert mock_session.commit.called
