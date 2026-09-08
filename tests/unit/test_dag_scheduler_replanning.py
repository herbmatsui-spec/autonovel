"""Integration tests for DAGScheduler Replanning (Part 5 / Step 60 / Checkpoint 10)."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.tasks.dag_replanning import DAGReplanningState


@pytest.mark.asyncio
async def test_scheduler_replan_node_and_execution_flow():
    """Verify replan_node resets target and downstream, allowing complete DAG execution."""
    registry = {
        "step_a": lambda: "result_a",
        "step_b": lambda **kw: f"result_b_{kw.get('val', 1)}",
        "step_c": lambda: "result_c",
    }

    g = DAGGraph(dag_id="replan_dag")
    g.add_node(DAGTaskNode(task_id="a", func_name="step_a"))
    g.add_node(DAGTaskNode(task_id="b", func_name="step_b", dependencies=["a"], kwargs={"val": 1}))
    g.add_node(DAGTaskNode(task_id="c", func_name="step_c", dependencies=["b"]))

    scheduler = DAGScheduler(task_registry=registry)

    # Initial run: completes all 3
    await scheduler.run_dag(g)
    assert g.is_all_completed()
    assert g.nodes["b"].result == "result_b_1"

    # Replan node "b" with new argument (simulating PDCA directive application)
    state = await scheduler.replan_node(
        g,
        target_node_id="b",
        new_kwargs={"val": 2},
        reason="PDCA score improvement",
    )

    assert isinstance(state, DAGReplanningState)
    assert state.trigger_node_id == "b"
    assert "c" in state.affected_downstream_ids
    assert g.nodes["b"].status == "pending"
    assert g.nodes["c"].status == "pending"
    assert g.nodes["a"].status == "completed"  # Upstream untouched

    # Run scheduler again to complete re-scheduled nodes
    await scheduler.run_dag(g)
    assert g.is_all_completed()
    assert g.nodes["b"].result == "result_b_2"
    assert g.nodes["c"].result == "result_c"

    # Execution summary check
    summary = scheduler.get_execution_summary(g)
    assert summary["replanning_count"] == 1
    assert summary["total_rescheduled_tasks"] >= 2


@pytest.mark.asyncio
async def test_scheduler_replan_max_limit_failsafe():
    """Verify exceeding max_replan_limit triggers a safe failure and aborts gracefully."""
    g = DAGGraph(dag_id="limit_dag")
    g.add_node(DAGTaskNode(task_id="node_x", func_name="dummy", retry_count=3))
    g.add_node(DAGTaskNode(task_id="node_y", func_name="dummy", dependencies=["node_x"]))

    scheduler = DAGScheduler()

    with pytest.raises(RuntimeError, match="Exceeded max replan limit"):
        await scheduler.replan_node(g, target_node_id="node_x", max_replan_limit=3)

    assert g.nodes["node_x"].status == "failed"
    assert g.nodes["node_y"].status == "cancelled"


@pytest.mark.asyncio
async def test_scheduler_replan_event_bus_publication():
    """Verify dag.replanned event is published to EventBus."""
    mock_bus = MagicMock()
    mock_bus.publish_async = AsyncMock()

    g = DAGGraph(dag_id="event_dag")
    g.add_node(DAGTaskNode(task_id="target", func_name="dummy"))

    scheduler = DAGScheduler(event_bus=mock_bus)
    await scheduler.replan_node(g, target_node_id="target", reason="Test event")

    assert mock_bus.publish_async.called
    event_type, payload = mock_bus.publish_async.call_args[0]
    assert event_type == "dag.replanned"
    assert payload["trigger_node_id"] == "target"
