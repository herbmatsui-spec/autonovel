"""Unit tests for DAGScheduler Part 5 (Steps 49-54): Timeouts, Cascade Cancellation, Huey Dispatch."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.tasks.resource_manager import ResourceManager


@pytest.mark.asyncio
async def test_cascade_cancel_downstream():
    """Test that downstream tasks are automatically cascade-cancelled when an upstream task fails."""
    graph = DAGGraph(dag_id="test_cascade")
    
    # A -> B -> C
    node_a = DAGTaskNode(task_id="A", func_name="fail_fn", retry_limit=0)
    node_b = DAGTaskNode(task_id="B", func_name="noop_fn", dependencies=["A"])
    node_c = DAGTaskNode(task_id="C", func_name="noop_fn", dependencies=["B"])
    
    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)

    def fail_fn():
        raise ValueError("Intentional crash")

    def noop_fn():
        return "ok"

    scheduler = DAGScheduler(task_registry={"fail_fn": fail_fn, "noop_fn": noop_fn})
    result_graph = await scheduler.run_dag(graph)

    assert result_graph.nodes["A"].status == "failed"
    assert result_graph.nodes["B"].status == "cancelled"
    assert result_graph.nodes["C"].status == "cancelled"
    assert "Dependency A failed" in (result_graph.nodes["B"].error or "")
    assert result_graph.is_finished() is True
    assert result_graph.is_all_completed() is False


@pytest.mark.asyncio
async def test_task_timeout_handling():
    """Test that a task that exceeds timeout_seconds is failed with timeout error."""
    graph = DAGGraph(dag_id="test_timeout")

    node_slow = DAGTaskNode(
        task_id="slow_task",
        func_name="slow_fn",
        timeout_seconds=0.1,
        retry_limit=0,
    )
    graph.add_node(node_slow)

    async def slow_fn():
        await asyncio.sleep(1.0)
        return "should not reach"

    scheduler = DAGScheduler(task_registry={"slow_fn": slow_fn})
    result_graph = await scheduler.run_dag(graph)

    assert result_graph.nodes["slow_task"].status == "failed"
    assert "Timeout after 0.1s" in (result_graph.nodes["slow_task"].error or "")


@pytest.mark.asyncio
async def test_dag_scheduler_huey_dispatch():
    """Test that DAGScheduler dispatches tasks to Huey when use_huey is enabled."""
    graph = DAGGraph(dag_id="test_huey_dispatch")
    node = DAGTaskNode(
        task_id="huey_node",
        func_name="agent_review",
        kwargs={"draft": "Some draft"},
    )
    graph.add_node(node)

    mock_huey = MagicMock()
    scheduler = DAGScheduler(huey_instance=mock_huey, use_huey=True)

    fake_huey_result = {"status": "completed", "output": "Review passed", "node_id": "huey_node"}

    with patch("src.backend.tasks.huey.execute_agent_node_task") as mock_exec, \
         patch("src.backend.tasks.huey.async_wait_huey_result", new_callable=AsyncMock) as mock_wait:
        
        mock_task = MagicMock()
        mock_exec.return_value = mock_task
        mock_wait.return_value = fake_huey_result

        result_graph = await scheduler.run_dag(graph)

        mock_exec.assert_called_once_with(
            func_name="agent_review",
            kwargs={"draft": "Some draft"},
            node_id="huey_node",
        )
        mock_wait.assert_called_once_with(mock_task, timeout=60.0)
        assert result_graph.nodes["huey_node"].status == "completed"
        assert result_graph.nodes["huey_node"].result == fake_huey_result


@pytest.mark.asyncio
async def test_is_finished_with_cancellations_and_successes():
    """Test that DAG finishes cleanly when some parallel branches succeed and others are cancelled."""
    graph = DAGGraph(dag_id="test_branches")

    # Branch 1: A (fails) -> B (cancelled)
    # Branch 2: X (succeeds) -> Y (succeeds)
    node_a = DAGTaskNode(task_id="A", func_name="fail_fn", retry_limit=0)
    node_b = DAGTaskNode(task_id="B", func_name="noop_fn", dependencies=["A"])
    node_x = DAGTaskNode(task_id="X", func_name="noop_fn")
    node_y = DAGTaskNode(task_id="Y", func_name="noop_fn", dependencies=["X"])

    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_x)
    graph.add_node(node_y)

    def fail_fn():
        raise RuntimeError("Branch 1 died")

    def noop_fn():
        return "branch ok"

    scheduler = DAGScheduler(task_registry={"fail_fn": fail_fn, "noop_fn": noop_fn})
    result_graph = await scheduler.run_dag(graph)

    assert result_graph.nodes["A"].status == "failed"
    assert result_graph.nodes["B"].status == "cancelled"
    assert result_graph.nodes["X"].status == "completed"
    assert result_graph.nodes["Y"].status == "completed"
    assert result_graph.is_finished() is True
