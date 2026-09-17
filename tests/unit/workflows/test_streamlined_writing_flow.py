import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.writing_langgraph import WritingGraphManager

@pytest.mark.asyncio
async def test_streamlined_writing_initial_state_limits():
    """v5.0: 初期状態のmax_ac_iterが1に制限され、start_timeが記録されることを検証"""
    manager = MagicMock()
    graph_mgr = WritingGraphManager(manager)
    state = graph_mgr._create_initial_state(
        ep_num=1,
        ctx={},
        sys_inst="inst",
        fw_prompt="fw",
        passion=0.8,
        is_easy_mode=False,
    )
    assert state["max_ac_iter"] == 1
    assert "start_time" in state
    assert time.time() >= state["start_time"]

@pytest.mark.asyncio
async def test_streamlined_writing_early_exit():
    """v5.0: 整合性・因果性合格時は無駄な再監査を行わず即座にfinishへEarly Exitすることを検証"""
    manager = MagicMock()
    graph_mgr = WritingGraphManager(manager)

    passing_state = {
        "ep_num": 1,
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "ac_iter": 0,
        "max_ac_iter": 1,
        "should_heavy_audit": True,
    }
    decision = graph_mgr._should_continue_critic(passing_state)
    assert decision == "finish"

@pytest.mark.asyncio
async def test_streamlined_writing_focused_patch_healing():
    """v5.0: actionable_patchが存在する場合、全文再生成を行わずに1パッチ置換が適用されることを検証"""
    manager = MagicMock()
    manager._phase_healing = AsyncMock() # 全文再生成モック
    graph_mgr = WritingGraphManager(manager)

    state = {
        "ep_num": 1,
        "draft_content": "初期の初稿本文。",
        "actionable_patch": "修正された追加パッチ段落。",
        "context": {"plot": MagicMock(detailed_blueprint="bp")},
        "causal_reason": "伏線未回収の指摘",
        "failures": [],
    }
    result = await graph_mgr.node_healing(state)

    assert result["is_causal_ok"] is True
    assert result["causal_reason"] == "healed_via_actionable_patch"
    assert "修正された追加パッチ段落。" in result["draft_content"]
    # 全文再生成の _phase_healing は一度も呼ばれていないことを検証（超高速・低コスト）
    manager._phase_healing.assert_not_called()
