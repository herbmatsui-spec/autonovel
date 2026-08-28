"""
tests/unit/test_review_nodes_affinity.py - Phase 3: Character Consistency and Affinity Auditing Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.nodes.review_nodes import (
    check_character_consistency_node,
    propose_edits_node,
)
from src.backend.workflows.state import ReviewGraphState


@pytest.mark.asyncio
async def test_check_character_consistency_with_affinity_map():
    """ステップ 42〜47: check_character_consistency_node の好感度監査テスト"""
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock(return_value=MagicMock(
        content='{"character_score": 0.6, "is_character_ok": false, "is_affinity_ok": false, "inconsistencies": ["好感度90なのに冷たい"], "affinity_issues": ["デレ期なのに急激な暴言"]}'
    ))

    state: ReviewGraphState = {
        "source_content": "「近寄らないで、最低な奴」エリスは冷たく言い放った。",
        "ep_num": 3,
        "metadata": {
            "affinity_map": {
                "エリス": {"affinity_score": 90.0, "current_mood": "deep_love"}
            }
        }
    }

    result = await check_character_consistency_node(state, llm_provider=mock_llm)
    assert result["status"] == "character_checked"
    consistency = result["character_consistency"]
    assert consistency["is_affinity_ok"] is False
    assert "デレ期なのに急激な暴言" in consistency["affinity_issues"]


@pytest.mark.asyncio
async def test_propose_edits_with_affinity_issues():
    """ステップ 48〜51: 好感度不整合がある場合に requires_revision=True となること"""
    state: ReviewGraphState = {
        "pacing_analysis": {"is_pacing_ok": True, "issues": []},
        "character_consistency": {
            "is_character_ok": True,
            "is_affinity_ok": False,
            "inconsistencies": [],
            "affinity_issues": ["ツンデレ期のセリフ不整合"],
        },
        "ep_num": 1,
    }

    result = await propose_edits_node(state)
    assert result["requires_revision"] is True
    assert any(iss["category"] == "Affinity" for iss in result["issues"])
    assert "ツンデレ期のセリフ不整合" in result["revision_instructions"]

