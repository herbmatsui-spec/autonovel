"""
tests/workflows/test_writing_hitl.py - Integration test for HITL review node within WritingGraph
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.graphs.writing_graph import create_writing_graph, compile_writing_graph
from src.backend.workflows.state import WritingGraphState
from src.backend.hitl_manager import HITLManager


@pytest.mark.asyncio
async def test_writing_graph_hitl_override_flow():
    """HITLが有効な場合、ドラフト生成後に一時停止し、ユーザーの上書きで本文が書き換わることを検証"""
    hitl_manager = HITLManager()
    session_id = "test-hitl-flow-01"

    graph = compile_writing_graph(hitl_manager=hitl_manager)

    initial_state: WritingGraphState = {
        "book_id": 1,
        "ep_num": 1,
        "enable_hitl": True,
        "hitl_session_id": session_id,
        "hitl_timeout": 5.0,
        "max_ac_iter": 1,
    }

    async def execute_graph():
        return await graph.ainvoke(initial_state)

    graph_task = asyncio.create_task(execute_graph())

    # Wait dynamically for graph to hit HITL suspend
    for _ in range(50):
        if any(p["session_id"] == session_id for p in hitl_manager.get_pending()):
            break
        await asyncio.sleep(0.05)

    pending = hitl_manager.get_pending()
    assert any(p["session_id"] == session_id for p in pending)

    # User reviews and overrides the draft
    overridden_text = "【ユーザー上書き本文】主人公は冷静に状況を分析し、秘密裏に行動を開始した。" * 30
    await hitl_manager.resume(
        session_id=session_id,
        response_data={
            "session_id": session_id,
            "approved": True,
            "feedback": "Great start, updated with specific tone",
            "overrides": {
                "draft_content": overridden_text,
            },
        },
    )

    final_state = await graph_task
    assert final_state["hitl_status"] == "resumed"
    assert "ユーザー上書き本文" in final_state["draft_content"]


@pytest.mark.asyncio
async def test_writing_graph_hitl_disabled_flow():
    """HITLが無効な場合、待機せず通常通り実行完了することを検証"""
    graph = compile_writing_graph()

    initial_state: WritingGraphState = {
        "book_id": 1,
        "ep_num": 2,
        "enable_hitl": False,
        "max_ac_iter": 1,
    }

    final_state = await graph.ainvoke(initial_state)
    assert final_state.get("hitl_status") == "skipped"
    assert "draft_content" in final_state
