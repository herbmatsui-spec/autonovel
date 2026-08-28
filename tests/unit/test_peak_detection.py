import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.nodes.writing_nodes import self_audit_node
from src.backend.workflows.state import WritingGraphState


@pytest.mark.asyncio
async def test_self_audit_node_peak_detection_with_llm():
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock(
        return_value=MagicMock(
            content={
                "is_integrity_ok": True,
                "is_causal_ok": True,
                "is_foreshadow_resolved": True,
                "event_density": 0.95,
                "score": 0.95,
                "failures": [],
                "detected_peaks": [
                    {
                        "scene_highlight": "主人公は覚醒し、闇の巨人を一閃のもとに切り伏せた。",
                        "peak_reason": "主人公の覚醒と敵ボスの撃破",
                        "intensity": 0.95,
                    }
                ],
            }
        )
    )

    state: WritingGraphState = {
        "ep_num": 5,
        "draft_content": "A" * 2000,
        "is_emotional_peak": True,
        "peak_reason": "覚醒シーン",
    }

    result = await self_audit_node(state, llm_provider=mock_llm)
    assert result["is_integrity_ok"] is True
    assert "detected_peaks" in result
    assert len(result["detected_peaks"]) == 1
    assert result["detected_peaks"][0]["peak_reason"] == "主人公の覚醒と敵ボスの撃破"


@pytest.mark.asyncio
async def test_self_audit_node_peak_fallback():
    # Test without LLM provider, should fallback to state's peak_reason
    state: WritingGraphState = {
        "ep_num": 3,
        "draft_content": "主人公はヒロインの手を握りしめ、二度と離さないと誓った。" + "B" * 2000,
        "is_emotional_peak": True,
        "peak_reason": "ヒロインへの誓い",
    }

    result = await self_audit_node(state, llm_provider=None)
    assert result["is_integrity_ok"] is True
    assert len(result["detected_peaks"]) == 1
    assert result["detected_peaks"][0]["peak_reason"] == "ヒロインへの誓い"
