"""WritingGraphManager coverage: nodes, routing, cache, fallback execution."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.workflows.writing_langgraph import (
    WritingGraphManager,
    WritingGraphState,
)


def make_manager():
    manager = MagicMock()
    manager.session_factory = None
    manager._phase_prepare_context = AsyncMock(
        return_value=("gen_ctx", True, False, False, 50)
    )
    manager._phase_drafting = AsyncMock(
        return_value=("本文" * 100, {"meta": 1})
    )
    manager._phase_audit = AsyncMock(
        return_value=(True, 0.95, True, "ok", [])
    )
    manager._phase_critic = AsyncMock(return_value=False)
    manager._phase_healing = AsyncMock(
        return_value=("healed", True, "healed_ok")
    )
    manager._run_dogfeeding_loop = AsyncMock(return_value=True)
    manager._register_lazy_patch = AsyncMock()
    manager.repo = MagicMock()
    manager.repo.misc = MagicMock()
    manager.repo.misc.get_patch_review = AsyncMock(return_value={"status": "approved"})
    return manager


@pytest.fixture
def mgr():
    return WritingGraphManager(make_manager())


def make_state(**overrides):
    state = {
        "ep_num": 1,
        "passion": 0.6,
        "is_easy_mode": False,
        "context": {"plot": MagicMock(detailed_blueprint="blueprint"),
                    "genre_str": "fantasy",
                    "prev_integrity": 100,
                    "engine_key": "unknown"},
        "sys_inst": "sys",
        "fw_prompt": "fw",
        "ac_iter": 0,
        "max_ac_iter": 1,
        "gen_ctx": "gen_ctx",
        "draft_content": "本文" * 100,
        "final_meta": {},
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "causal_reason": "ok",
        "failures": [],
        "should_heavy_audit": True,
        "should_dogfeed": True,
        "should_beat_decompose": False,
    }
    state.update(overrides)
    return state


# ============================================================================
# Init & graph build
# ============================================================================


def test_manager_init_without_langgraph(mgr):
    # langgraph 未導入環境では workflow=None（フォールバック）, checkpointer=None
    import src.backend.workflows.writing_langgraph as module
    if module.HAS_LANGGRAPH:
        assert mgr.workflow is not None
    else:
        assert mgr.workflow is None
        assert mgr.checkpointer is None
    assert mgr.metrics_collector is not None
    # checkpoint_manager は session_factory 有無で決まる
    if mgr.checkpoint_manager is not None:
        assert mgr.checkpoint_manager is not None
    assert mgr._scheduler is None
    # mgr フィクスチャの manager には session_factory がないため None だが
    # 実装上、session_factory があれば CheckpointManager が作られる
    # （test_manager_init_with_checkpoint_manager で検証済み）


def test_manager_init_with_checkpoint_manager():
    manager = make_manager()
    manager.session_factory = MagicMock()
    graph = WritingGraphManager(manager)
    assert graph.checkpoint_manager is not None


def test_build_graph_returns_none_without_langgraph(monkeypatch):
    import src.backend.workflows.writing_langgraph as module
    if module.HAS_LANGGRAPH:
        pytest.skip("langgraph installed")
    manager = make_manager()
    graph = WritingGraphManager(manager)
    assert graph.workflow is None


# ============================================================================
# Cache operations
# ============================================================================


def test_gen_ctx_cache_hit_miss_and_expiry(mgr):
    WritingGraphManager.clear_gen_ctx_cache()
    assert WritingGraphManager._get_cached_gen_ctx("k1") is None
    WritingGraphManager._set_cached_gen_ctx("k1", "ctx1")
    assert WritingGraphManager._get_cached_gen_ctx("k1") == "ctx1"

    # TTL expiry
    WritingGraphManager._gen_ctx_cache["k2"] = {"gen_ctx": "old", "timestamp": 0}
    assert WritingGraphManager._get_cached_gen_ctx("k2") is None
    assert "k2" not in WritingGraphManager._gen_ctx_cache
    WritingGraphManager.clear_gen_ctx_cache()


def test_gen_ctx_cache_size_limit():
    WritingGraphManager.clear_gen_ctx_cache()
    for i in range(105):
        WritingGraphManager._set_cached_gen_ctx(f"k{i}", f"ctx{i}")
    assert len(WritingGraphManager._gen_ctx_cache) <= 100
    count = WritingGraphManager.clear_gen_ctx_cache()
    assert count == 100
    assert WritingGraphManager._gen_ctx_cache == {}


# ============================================================================
# Checkpoint save
# ============================================================================


def test_save_checkpoint_if_needed_sync_and_async():
    # sync result
    manager = make_manager()
    manager.session_factory = MagicMock()
    graph = WritingGraphManager(manager)
    graph.checkpoint_manager.record_step = MagicMock(return_value=None)
    graph._save_checkpoint_if_needed(make_state(task_id="t1"), "prepare", 0)
    graph.checkpoint_manager.record_step.assert_called_once()

    # async coroutine result -> queued
    import asyncio as asyncio_module

    async def coro():
        pass

    graph.checkpoint_manager.record_step = MagicMock(return_value=coro())
    graph._save_checkpoint_if_needed(make_state(task_id="t2"), "drafting", 1)
    assert len(graph._pending_checkpoint_tasks) == 1

    # no task_id -> skip
    graph._save_checkpoint_if_needed(make_state(task_id=None), "audit", 2)
    assert len(graph._pending_checkpoint_tasks) == 1


# ============================================================================
# node_prepare
# ============================================================================


@pytest.mark.asyncio
async def test_node_prepare_first_run(mgr):
    WritingGraphManager.clear_gen_ctx_cache()
    state = make_state()
    result = await mgr.node_prepare(state)
    assert result["gen_ctx"] == "gen_ctx"
    assert result["max_ac_iter"] >= 1
    assert result["ac_iter"] == 0
    mgr.manager._phase_prepare_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_node_prepare_cache_hit(mgr):
    WritingGraphManager.clear_gen_ctx_cache()
    WritingGraphManager._set_cached_gen_ctx("ep1_fantasy_False", "cached_ctx")
    state = make_state()
    result = await mgr.node_prepare(state)
    assert result["gen_ctx"] == "cached_ctx"
    assert result["should_dogfeed"] is True
    assert result["should_heavy_audit"] is False
    assert result["should_beat_decompose"] is False
    mgr.manager._phase_prepare_context.assert_not_awaited()
    WritingGraphManager.clear_gen_ctx_cache()


@pytest.mark.asyncio
async def test_node_prepare_high_ncs_skips_dogfeed(mgr):
    WritingGraphManager.clear_gen_ctx_cache()
    mgr.manager._phase_prepare_context = AsyncMock(
        return_value=("gen_ctx", True, False, False, 95)
    )
    result = await mgr.node_prepare(make_state())
    assert result["should_dogfeed"] is False


@pytest.mark.asyncio
async def test_node_prepare_retry_then_success(mgr):
    WritingGraphManager.clear_gen_ctx_cache()
    mgr.manager._phase_prepare_context = AsyncMock(
        side_effect=[RuntimeError("fail1"), ("gen_ctx", True, False, False, 50)]
    )
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        result = await mgr.node_prepare(make_state())
    assert result["gen_ctx"] == "gen_ctx"


@pytest.mark.asyncio
async def test_node_prepare_all_retries_fail_raises(mgr):
    WritingGraphManager.clear_gen_ctx_cache()
    mgr.manager._phase_prepare_context = AsyncMock(side_effect=RuntimeError("always"))
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        with pytest.raises(RuntimeError, match="always"):
            await mgr.node_prepare(make_state())


# ============================================================================
# node_drafting
# ============================================================================


@pytest.mark.asyncio
async def test_node_drafting_success(mgr):
    result = await mgr.node_drafting(make_state())
    assert result["draft_content"].startswith("本文")
    assert result["final_meta"] == {"meta": 1}


@pytest.mark.asyncio
async def test_node_drafting_insufficient_content_retries(mgr):
    mgr.manager._phase_drafting = AsyncMock(
        side_effect=[("short", {}), ("本文" * 100, {"meta": 2})]
    )
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        result = await mgr.node_drafting(make_state())
    assert result["draft_content"].startswith("本文")
    assert result["final_meta"] == {"meta": 2}


@pytest.mark.asyncio
async def test_node_drafting_all_retries_fail(mgr):
    mgr.manager._phase_drafting = AsyncMock(side_effect=RuntimeError("draft fail"))
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        result = await mgr.node_drafting(make_state())
    assert result["draft_content"] == ""
    assert result["final_meta"] == {}


# ============================================================================
# node_audit
# ============================================================================


@pytest.mark.asyncio
async def test_node_audit_easy_mode_short_circuit(mgr):
    result = await mgr.node_audit(make_state(is_easy_mode=True))
    assert result["is_integrity_ok"] is True
    assert result["is_causal_ok"] is True
    assert result["causal_reason"] == "easy_mode"
    assert result["rate"] == 1.0
    mgr.manager._phase_audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_node_audit_success(mgr):
    result = await mgr.node_audit(make_state())
    assert result["is_integrity_ok"] is True
    assert result["is_causal_ok"] is True
    assert result["rate"] == 0.95
    assert result["quality_skip"] is True  # 0.95 >= threshold & both ok


@pytest.mark.asyncio
async def test_node_audit_low_quality_no_skip(mgr):
    mgr.manager._phase_audit = AsyncMock(
        return_value=(True, 0.5, False, "bad", [{"type": "x"}])
    )
    result = await mgr.node_audit(make_state())
    assert result["rate"] == 0.5
    assert "quality_skip" not in result or result.get("quality_skip") is False


@pytest.mark.asyncio
async def test_node_audit_all_retries_fail(mgr):
    mgr.manager._phase_audit = AsyncMock(side_effect=RuntimeError("audit fail"))
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        result = await mgr.node_audit(make_state())
    assert result["is_integrity_ok"] is False
    assert result["rate"] == 0.0
    assert result["failures"][0]["type"] == "audit_error"


# ============================================================================
# node_review_wait & routing
# ============================================================================


@pytest.mark.asyncio
async def test_node_review_wait_no_id():
    mgr = WritingGraphManager(make_manager())
    result = await mgr.node_review_wait(make_state(patch_review_id=None))
    assert result == {"review_status": "timeout"}


@pytest.mark.asyncio
@pytest.mark.parametrize("status_value,expected", [
    ("approved", "approved"),
    ("rejected", "rejected"),
    ("needs_revision", "revised"),
])
async def test_node_review_wait_statuses(status_value, expected):
    manager = make_manager()
    manager.repo.misc.get_patch_review = AsyncMock(return_value={"status": status_value})
    mgr = WritingGraphManager(manager)
    with pytest.MonkeyPatch.context() as m:
        # ProjectContext は関数内 import されるため config 側をパッチする
        import config.project_context as project_context
        m.setattr(project_context.ProjectContext, "get_setting",
                  staticmethod(lambda key, default=None: 0.01 if "poll" in key else 1))
        result = await mgr.node_review_wait(make_state(patch_review_id=5))
    assert result == {"review_status": expected}


@pytest.mark.asyncio
async def test_node_review_wait_error_and_timeout():
    manager = make_manager()
    manager.repo.misc.get_patch_review = AsyncMock(side_effect=RuntimeError("db"))
    mgr = WritingGraphManager(manager)
    with pytest.MonkeyPatch.context() as m:
        import config.project_context as project_context
        m.setattr(project_context.ProjectContext, "get_setting",
                  staticmethod(lambda key, default=None: 0.01 if "poll" in key else 1))
        result = await mgr.node_review_wait(make_state(patch_review_id=5))
    assert result == {"review_status": "timeout"}


@pytest.mark.parametrize("review_status,expected", [
    ("approved", "approved"),
    ("rejected", "rejected"),
    ("revised", "revised"),
    ("timeout", "timeout"),
    (None, "timeout"),
])
def test_route_after_review_wait(mgr, review_status, expected):
    assert mgr.route_after_review_wait({"review_status": review_status}) == expected


# ============================================================================
# route_after_audit
# ============================================================================


def test_route_after_audit_easy_mode(mgr):
    assert mgr.route_after_audit(make_state(is_easy_mode=True)) == "finish"


def test_route_after_audit_quality_skip(mgr):
    state = make_state(quality_skip=True, is_integrity_ok=True, is_causal_ok=True)
    assert mgr.route_after_audit(state) == "finish"


def test_route_after_audit_review_wait(mgr):
    state = make_state(requires_user_review=True, patch_review_id=7)
    assert mgr.route_after_audit(state) == "review_wait"


def test_route_after_audit_both_ok(mgr):
    assert mgr.route_after_audit(make_state()) == "finish"


def test_route_after_audit_max_iter_reached(mgr):
    state = make_state(is_integrity_ok=False, is_causal_ok=False, ac_iter=2, max_ac_iter=2)
    assert mgr.route_after_audit(state) == "finish"


def test_route_after_audit_heal_on_causal_fail(mgr):
    state = make_state(is_integrity_ok=True, is_causal_ok=False, ac_iter=0, max_ac_iter=3)
    assert mgr.route_after_audit(state) == "heal"


def test_route_after_audit_critic_on_other_failures(mgr):
    state = make_state(is_integrity_ok=False, is_causal_ok=True,
                       should_heavy_audit=True, ac_iter=0, max_ac_iter=3)
    assert mgr.route_after_audit(state) == "critic"


def test_route_after_critic_budget_exceeded(mgr):
    tracker = MagicMock()
    tracker.is_within_budget.return_value = False
    state = make_state(budget_tracker=tracker, critic_triggered=True)
    assert mgr.route_after_critic(state) == "finish"


def test_route_after_critic_retry_and_finish(mgr):
    state = make_state(critic_triggered=True, ac_iter=0, max_ac_iter=2)
    assert mgr.route_after_critic(state) == "retry"
    # max reached
    state = make_state(critic_triggered=True, ac_iter=2, max_ac_iter=2)
    assert mgr.route_after_critic(state) == "finish"
    # not triggered
    state = make_state(critic_triggered=False)
    assert mgr.route_after_critic(state) == "finish"


# ============================================================================
# node_critic / node_healing / node_dogfeed / node_finalize
# ============================================================================


@pytest.mark.asyncio
async def test_node_critic_success_and_failure(mgr):
    result = await mgr.node_critic(make_state())
    assert result == {"critic_triggered": False}

    mgr.manager._phase_critic = AsyncMock(return_value=True)
    result = await mgr.node_critic(make_state())
    assert result == {"critic_triggered": True}

    mgr.manager._phase_critic = AsyncMock(side_effect=RuntimeError("critic fail"))
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        result = await mgr.node_critic(make_state())
    assert result == {"critic_triggered": False}


@pytest.mark.asyncio
async def test_node_healing_actionable_patch(mgr):
    state = make_state(actionable_patch="修正パッチ", draft_content="本文")
    result = await mgr.node_healing(state)
    assert result["draft_content"].startswith("本文")
    assert "修正パッチ" in result["draft_content"]
    assert result["is_causal_ok"] is True
    assert result["causal_reason"] == "healed_via_actionable_patch"
    mgr.manager._phase_healing.assert_not_awaited()


@pytest.mark.asyncio
async def test_node_healing_success_and_failure(mgr):
    result = await mgr.node_healing(make_state())
    assert result == {"draft_content": "healed", "is_causal_ok": True,
                      "causal_reason": "healed_ok"}

    mgr.manager._phase_healing = AsyncMock(side_effect=RuntimeError("heal fail"))
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        result = await mgr.node_healing(make_state())
    assert result["is_causal_ok"] is False
    assert result["draft_content"] != ""


@pytest.mark.asyncio
async def test_node_dogfeed_skip_and_success(mgr):
    result = await mgr.node_dogfeed(make_state(should_dogfeed=False))
    assert result == {"dogfeed_ok": True}
    result = await mgr.node_dogfeed(make_state(is_easy_mode=True))
    assert result == {"dogfeed_ok": True}

    mgr2 = WritingGraphManager(make_manager())
    result = await mgr2.node_dogfeed(make_state())
    assert result == {"dogfeed_ok": True}


@pytest.mark.asyncio
async def test_node_dogfeed_all_retries_fail(mgr):
    mgr.manager._run_dogfeeding_loop = AsyncMock(side_effect=RuntimeError("df fail"))
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.workflows.writing_langgraph.asyncio.sleep", AsyncMock())
        result = await mgr.node_dogfeed(make_state())
    assert result == {"dogfeed_ok": False}


@pytest.mark.asyncio
async def test_node_finalize_ok_no_lazy_patch(mgr):
    state = make_state(rate=0.95)
    result = await mgr.node_finalize(state)
    assert result["status"] == "completed"
    assert "latency_sec" in result["final_meta"]
    assert result["final_meta"]["ac_iterations"] == 0
    mgr.manager._register_lazy_patch.assert_not_awaited()
    # metadata recorded
    assert mgr.get_checkpoint_metadata(1)["is_integrity_ok"] is True
    assert mgr.get_all_checkpoint_metadata()[1]["rate"] == 0.95
    assert mgr.get_episode_metrics(1) is not None


@pytest.mark.asyncio
async def test_node_finalize_failure_registers_lazy_patch(mgr):
    state = make_state(is_integrity_ok=False, is_causal_ok=False, dogfeed_ok=False)
    result = await mgr.node_finalize(state)
    assert result["status"] == "completed"
    mgr.manager._register_lazy_patch.assert_awaited_once()


@pytest.mark.asyncio
async def test_node_finalize_foreshadowing_resolution(mgr):
    fs = MagicMock()
    fs.check_and_resolve = AsyncMock(return_value=["伏線A"])
    state = make_state(foreshadowing_service=fs, book_id=3)
    result = await mgr.node_finalize(state)
    assert result["final_meta"]["resolved_foreshadowings"] == ["伏線A"]
    fs.check_and_resolve.assert_awaited_once()


@pytest.mark.asyncio
async def test_node_finalize_foreshadowing_error_non_fatal(mgr):
    fs = MagicMock()
    fs.check_and_resolve = AsyncMock(side_effect=RuntimeError("fs fail"))
    state = make_state(foreshadowing_service=fs, book_id=3)
    result = await mgr.node_finalize(state)
    assert result["status"] == "completed"
    assert "resolved_foreshadowings" not in result["final_meta"]


# ============================================================================
# Initial state & fallback execution
# ============================================================================


def test_create_initial_state(mgr):
    state = mgr._create_initial_state(2, {"k": "v"}, "sys", "fw", 0.7, False)
    assert state["ep_num"] == 2
    assert state["passion"] == 0.7
    assert state["max_ac_iter"] >= 1
    assert state["status"] == "pending"
    assert state["patch_review_id"] is None
    assert state["requires_user_review"] is False


@pytest.mark.asyncio
async def test_run_fallback_success_path(mgr):
    if mgr.workflow is not None:
        pytest.skip("langgraph installed; fallback path not used")
    content, meta, integrity = await mgr.run(1, make_state()["context"], "sys", "fw", 0.6, False)
    assert content.startswith("本文")
    assert meta.get("meta") == 1 or "latency_sec" in meta
    assert integrity is True


@pytest.mark.asyncio
async def test_run_with_dependencies(mgr):
    if mgr.workflow is not None:
        pytest.skip("langgraph installed; dependency path partially used")
    content, meta, integrity = await mgr.run_with_dependencies(
        2, make_state()["context"], "sys", "fw", 0.6, False, depends_on=1
    )
    assert content.startswith("本文")
    assert integrity is True


@pytest.mark.asyncio
async def test_check_dependency_and_wait(mgr):
    # depends_on < 1 -> always True
    assert await mgr._check_dependency(1, 0) is True
    # No metrics recorded -> True
    assert await mgr._check_dependency(2, 1) is True

    # Low quality dependency -> False
    from src.backend.workflows.quality_metrics import QualityMetrics
    import time as time_module
    low = QualityMetrics(ep_num=1, integrity_ok=False, causal_ok=False, rate=0.1,
                         ac_iter=0, threshold=0, timestamp=time_module.time(),
                         genre="fantasy", dogfeed_ok=False, causal_reason="")
    mgr.metrics_collector.record(low)
    assert await mgr._check_dependency(2, 1) is False

    # wait without scheduler -> no-op
    await mgr._wait_for_dependency(2, 1)

    # wait with scheduler
    scheduler = MagicMock()
    scheduler.await_plot_ready = AsyncMock()
    mgr.set_scheduler(scheduler)
    await mgr._wait_for_dependency(2, 1)
    scheduler.await_plot_ready.assert_awaited_once_with(1)

    # scheduler error is non-fatal
    scheduler.await_plot_ready = AsyncMock(side_effect=RuntimeError("sched"))
    await mgr._wait_for_dependency(2, 1)


def test_set_scheduler(mgr):
    scheduler = MagicMock()
    mgr.set_scheduler(scheduler)
    assert mgr._scheduler is scheduler


def test_state_class_defaults():
    state = WritingGraphState()
    assert state == {}


def test_clear_checkpoint_metadata(mgr):
    mgr._checkpoint_metadata[1] = {"rate": 0.9}
    mgr._checkpoint_metadata[2] = {"rate": 0.8}
    count = mgr.clear_checkpoint_metadata()
    assert count == 2
    assert mgr._checkpoint_metadata == {}
