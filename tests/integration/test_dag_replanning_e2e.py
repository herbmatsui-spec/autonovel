"""E2E Integration Test: DAG Replanning & Localized Retry on Audit Failure (Step 67).

Validates the full dynamic workflow:
Audit failure -> Downstream task cancellation & rollback -> Localized node retry ->
Automatic reactivation -> EventBus notification -> Successful DAG completion.
"""

import asyncio
import pytest
from unittest.mock import MagicMock

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode
from src.backend.tasks.dag_replanning import DAGReplanningState, DAGReplanner
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.services.commercial_benchmarks import CommercialBenchmarkJudge


@pytest.mark.asyncio
async def test_dag_replanning_and_localized_retry_e2e():
    """Test full E2E flow where an audit failure triggers DAG replanning and successful recovery."""
    event_bus = MagicMock()
    from unittest.mock import AsyncMock
    event_bus.publish_async = AsyncMock()

    # Track draft version
    draft_version = 1

    def outline_func():
        return "Outline generated: Protagonist begins journey"

    def draft_func(pdca_directives: str = ""):
        nonlocal draft_version
        if draft_version == 1:
            return "Draft v1: Plain battle scene without emotional tension."
        return f"Draft v2 (Revised with: {pdca_directives}): High tension battle with deep character focus."

    def audit_func():
        nonlocal draft_version
        if draft_version == 1:
            return {"score": 58.0, "status": "failed"}
        return {"score": 87.0, "status": "passed"}

    def illustration_func():
        return "Illustration generated matching draft."

    def export_func():
        return "EPUB generated successfully."

    task_registry = {
        "outline": outline_func,
        "draft": draft_func,
        "audit": audit_func,
        "illustration": illustration_func,
        "export": export_func,
    }

    scheduler = DAGScheduler(task_registry=task_registry, event_bus=event_bus)

    # 1. Build DAG pipeline:
    # outline -> draft -> [audit, illustration] -> export
    g = DAGGraph(dag_id="dag_e2e_pdca")
    g.add_node(DAGTaskNode(task_id="outline", func_name="outline"))
    g.add_node(DAGTaskNode(task_id="draft", func_name="draft", dependencies=["outline"]))
    g.add_node(DAGTaskNode(task_id="audit", func_name="audit", dependencies=["draft"]))
    g.add_node(DAGTaskNode(task_id="illustration", func_name="illustration", dependencies=["draft"]))
    g.add_node(DAGTaskNode(task_id="export", func_name="export", dependencies=["audit", "illustration"]))

    # 2. Run initial execution
    await scheduler.run_dag(g)
    assert g.is_all_completed()
    audit_res = g.nodes["audit"].result
    assert audit_res["status"] == "failed"

    # Evaluate benchmark on round 1 (fails fatal flaw)
    initial_quality = CommercialBenchmarkJudge.evaluate_quality(
        58.0,
        {"structure_score": 58.0, "coherency_score": 68.0},
    )
    assert initial_quality.has_no_fatal_flaws is False
    assert initial_quality.is_commercial_ready is False

    # 3. Simulate Failure -> Trigger DAG Replanning for 'draft'
    draft_version = 2
    state = await scheduler.replan_node(
        g,
        target_node_id="draft",
        new_kwargs={"pdca_directives": "感情振幅と読者フックの徹底強化"},
        reason="Audit failed with fatal flaw in structure",
    )

    # 4. Verify rollback state
    assert isinstance(state, DAGReplanningState)
    assert state.trigger_node_id == "draft"
    assert g.nodes["draft"].status == "pending"
    assert g.nodes["draft"].retry_count == 1
    assert "感情振幅" in g.nodes["draft"].kwargs["pdca_directives"]

    # Downstream nodes reset
    assert g.nodes["audit"].status == "pending"
    assert g.nodes["illustration"].status == "pending"
    assert g.nodes["export"].status == "pending"

    # Upstream node untouched
    assert g.nodes["outline"].status == "completed"

    # 5. Verify EventBus notification
    assert event_bus.publish_async.called
    call_args = [call[0] for call in event_bus.publish_async.call_args_list]
    event_names = [arg[0] for arg in call_args if len(arg) > 0]
    assert "dag.replanned" in event_names

    # 6. Re-run DAG
    await scheduler.run_dag(g)
    assert g.is_all_completed()

    # Verify new results
    assert "Draft v2" in g.nodes["draft"].result
    revised_audit_res = g.nodes["audit"].result
    assert revised_audit_res["status"] == "passed"
    assert revised_audit_res["score"] == 87.0

    # 7. Quality evaluation on round 2 -> S rank achieved
    revised_quality = CommercialBenchmarkJudge.evaluate_quality(
        87.0,
        {"structure_score": 88.0, "coherency_score": 86.0},
    )
    assert revised_quality.is_commercial_ready is True
    assert revised_quality.has_no_fatal_flaws is True
    assert revised_quality.rank == "S"

    passed, rate = CommercialBenchmarkJudge.validate_pdca_improvement(58.0, 87.0)
    assert passed is True
    assert rate == 50.0
