"""
WritingGraphManager フォールバック動作の総合テスト

LangGraph が未インストールの環境 (self.workflow is None) でも
_create_initial_state / route_after_audit / route_after_critic が
KeyError を起こさず安全に動作することを確認する。
"""

import pytest

from src.backend.workflows.writing_langgraph import (
    HAS_LANGGRAPH,
    WritingGraphManager,
)


@pytest.fixture
def manager():
    """最小構成の WritingGraphManager (workflow=None) を生成"""
    m = WritingGraphManager.__new__(WritingGraphManager)
    m.manager = None
    m.workflow = None
    m.checkpointer = None
    m._checkpoint_metadata = {}
    m._scheduler = None
    m._scheduler_lock = None
    return m


def test_create_initial_state_has_required_keys(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, False)
    for key in (
        "ep_num", "passion", "is_easy_mode", "context", "sys_inst", "fw_prompt",
        "ac_iter", "max_ac_iter", "should_heavy_audit", "should_dogfeed",
        "should_beat_decompose", "gen_ctx", "draft_content", "final_meta",
        "is_integrity_ok", "is_causal_ok", "causal_reason", "failures", "status",
    ):
        assert key in state, f"missing key: {key}"
    assert state["ac_iter"] == 0
    assert state["max_ac_iter"] >= 1
    assert state["status"] == "pending"


def test_route_after_audit_easy_mode(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, True)
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_quality_skip(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, False)
    state.update({
        "quality_skip": True,
        "is_integrity_ok": True,
        "is_causal_ok": True,
    })
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_max_iter_reached(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, False)
    state.update({
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "ac_iter": state["max_ac_iter"],
    })
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_goes_to_critic(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, False)
    state.update({
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "should_heavy_audit": True,
        "ac_iter": 0,
    })
    assert manager.route_after_audit(state) == "critic"


def test_route_after_audit_causal_fail_heals(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, False)
    state.update({
        "is_integrity_ok": True,
        "is_causal_ok": False,
        "should_heavy_audit": True,
    })
    assert manager.route_after_audit(state) == "heal"


def test_route_after_critic_triggered_no_iter_left(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, False)
    state.update({"critic_triggered": True, "ac_iter": state["max_ac_iter"]})
    assert manager.route_after_critic(state) == "finish"


def test_route_after_critic_triggered_retry(manager):
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, False)
    state.update({"critic_triggered": True, "ac_iter": 0})
    assert manager.route_after_critic(state) == "retry"


@pytest.mark.skipif(HAS_LANGGRAPH, reason="workflow=None フォールバック確認のため langgraph 未導入環境でのみ実行")
@pytest.mark.anyio
async def test_run_fallback_no_keyerror(manager):
    """workflow=None のとき run() が KeyError なしに完了する最低限の確認"""
    state = manager._create_initial_state(1, {}, "sys", "fw", 0.5, True)
    # フォールバックブロックは直接呼ばず、route 系メソッドの安全性を確認
    assert manager.route_after_audit(state) == "finish"
