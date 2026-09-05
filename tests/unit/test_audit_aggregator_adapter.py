# tests/unit/test_audit_aggregator_adapter.py
"""Unit tests for AuditAggregatorNode pipeline adapter."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.orchestrator import AgentContext, AgentName, AgentResult
from src.agents.specialists.adapter import (
    AuditAggregatorNode,
    create_default_specialists,
    load_audit_weights,
)
from src.services.audit_aggregator import AuditAggregator, BookScoreResult


def test_create_default_specialists():
    """Verify standard 8 specialists are instantiated."""
    specialists = create_default_specialists()
    assert len(specialists) == 8
    names = {s.specialist_name for s in specialists}
    expected = {
        "consistency",
        "creativity",
        "reader_hook",
        "emotion_curve",
        "style",
        "factual",
        "structure",
        "multimodal",
    }
    assert names == expected


def test_load_audit_weights():
    """Verify loading audit weights and normalization."""
    weights = load_audit_weights("config/audit_weights.yaml")
    assert len(weights) == 8
    assert pytest.approx(sum(weights.values()), rel=1e-5) == 1.0


def test_build_specialist_input():
    """Verify converting AgentContext to specialist input dict."""
    node = AuditAggregatorNode()
    ctx = AgentContext(
        book_id=42,
        branch_id=1,
        ep_num=3,
        artifacts={
            "drafted_text": "主人公は剣を抜いた。生きて帰るために。",
            "writing_context": {"characters": ["主人公"]},
            "genre": "action",
        },
    )
    data = node.build_specialist_input(ctx)
    assert data["book_id"] == 42
    assert data["ep_num"] == 3
    assert data["draft_text"] == "主人公は剣を抜いた。生きて帰るために。"
    assert data["genre"] == "action"


def test_to_agent_result():
    """Verify converting BookScoreResult to AgentResult."""
    node = AuditAggregatorNode()
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1)
    score_result = BookScoreResult(
        overall=82.5,
        by_specialist={"consistency": 85.0, "creativity": 80.0},
        missing=[],
        weights_used={"consistency": 0.5, "creativity": 0.5},
    )
    result = node.to_agent_result(score_result, ctx)
    assert isinstance(result, AgentResult)
    assert result.next_agent == AgentName.ILLUSTRATION
    assert result.artifacts["audit_score"] == 82.5
    assert result.artifacts["lowest_dimension"] == "creativity"
    assert result.error is None


@pytest.mark.asyncio
async def test_audit_aggregator_node_execution():
    """Verify full execution of AuditAggregatorNode."""
    node = AuditAggregatorNode()
    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={
            "drafted_text": "城門の前で、主人公は静かに剣の柄に手を置いた。雨が石畳を濡らしている。",
            "world_bible_snapshot": {
                "characters": [{"name": "主人公"}],
                "locations": ["城門"],
            },
        },
    )
    result = await node(ctx)
    assert result.next_agent == AgentName.ILLUSTRATION
    assert "audit_score" in result.artifacts
    assert isinstance(result.artifacts["audit_score"], float)
    assert "specialist_scores" in result.artifacts
    assert len(result.artifacts["specialist_scores"]) == 8
