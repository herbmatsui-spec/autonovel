"""Unit tests for BlindReview Purifier (Part 1 / Checkpoint 1: Steps 1-6)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.services.blind_review import (
    PurifiedFeedback,
    detect_proposal_leaks,
    BlindFeedbackPurifier,
    BlindReviewGate,
)


def test_detect_proposal_leaks():
    """Test detection of proposal leak phrases."""
    text = "A案の主人公の行動は性急であり、案2における世界観設定と矛盾している。また候補Bの結末も気になる。"
    leaks = detect_proposal_leaks(text)
    assert len(leaks) >= 3
    assert any("A案" in l for l in leaks)
    assert any("案2" in l for l in leaks)
    assert any("候補B" in l for l in leaks)


def test_blind_feedback_purifier_rule_based():
    """Test rule-based purification of critique without LLM."""
    purifier = BlindFeedbackPurifier()
    critique = "A案の主人公の動機が希薄である。本作の序盤の葛藤を強化すべき。"
    res = purifier.purify_critique(critique, forbidden_terms=["A案の主人公"])

    assert res.is_purified is True
    assert "A案" not in res.purified_text
    assert "序盤の葛藤を強化すべき" in res.purified_text
    assert len(res.removed_entities) > 0


@pytest.mark.asyncio
async def test_blind_feedback_purifier_async_llm():
    """Test LLM-based purification with fallback."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="主人公の動機を明確にし、序盤の葛藤をもっと早く提示すべき。")

    purifier = BlindFeedbackPurifier(llm_adapter=mock_llm)
    critique = "B案では魔王討伐が唐突すぎる。もっと序盤の葛藤を早く出すべき。"

    res = await purifier.purify_critique_async(critique)
    assert res.is_purified is True
    assert "B案" not in res.purified_text
    assert "魔王討伐" not in res.purified_text
    assert "序盤の葛藤をもっと早く提示すべき" in res.purified_text


def test_blind_review_gate_with_purify_text():
    """Test BlindReviewGate automatic text purification on payload."""
    gate = BlindReviewGate(
        forbidden_agents=["proposal_a", "proposal_b"],
        purify_text=True,
    )

    payload = {
        "status": "success",
        "feedback": {
            "critique": "A案のストーリー展開は面白いが、案Bと比べてテンポが遅い。",
            "general_score": 80,
        },
        "proposal_a_notes": "Secret idea for A",
    }

    scrubbed = gate.scrub_payload(payload)

    # Key blocking should still work
    assert scrubbed["proposal_a_notes"] == "<BLOCKED:proposal_a>"

    # Text purification should clean the critique text
    critique_text = scrubbed["feedback"]["critique"]
    assert "A案" not in critique_text
    assert "案B" not in critique_text
    assert scrubbed["feedback"]["general_score"] == 80
