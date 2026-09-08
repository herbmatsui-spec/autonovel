"""Unit tests for DAGScheduler Part 5 (Steps 55-60): EventBus, Execution Summary, DAG Pipeline, and Status Endpoint."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.tasks.generation_tasks import build_novel_generation_dag, run_novel_dag_pipeline_async
from src.backend.server import app


@pytest.mark.asyncio
async def test_event_bus_publishing():
    """Test that DAGScheduler publishes lifecycle events to the provided EventBus."""
    graph = DAGGraph(dag_id="test_events_dag")
    node = DAGTaskNode(task_id="task_1", func_name="dummy_work")
    graph.add_node(node)

    events_received = []

    mock_event_bus = MagicMock()
    async def fake_publish_async(event_type: str, payload: dict):
        events_received.append((event_type, payload))

    mock_event_bus.publish_async = fake_publish_async

    scheduler = DAGScheduler(
        task_registry={"dummy_work": lambda: "done"},
        event_bus=mock_event_bus,
    )
    await scheduler.run_dag(graph)

    event_types = [e[0] for e in events_received]
    assert "dag.task_started" in event_types
    assert "dag.task_completed" in event_types
    assert "dag.completed" in event_types


@pytest.mark.asyncio
async def test_get_execution_summary():
    """Test that get_execution_summary accurately reports counts, percentages, and details."""
    graph = DAGGraph(dag_id="test_summary_dag")
    node_1 = DAGTaskNode(task_id="t1", name="Task 1", func_name="fn1", status="completed")
    node_2 = DAGTaskNode(task_id="t2", name="Task 2", func_name="fn2", status="failed", error="Fatal error")
    node_3 = DAGTaskNode(task_id="t3", name="Task 3", func_name="fn3", status="cancelled")
    node_4 = DAGTaskNode(task_id="t4", name="Task 4", func_name="fn4", status="pending")

    graph.add_node(node_1)
    graph.add_node(node_2)
    graph.add_node(node_3)
    graph.add_node(node_4)

    scheduler = DAGScheduler()
    summary = scheduler.get_execution_summary(graph)

    assert summary["dag_id"] == "test_summary_dag"
    assert summary["total_nodes"] == 4
    assert summary["status_counts"]["completed"] == 1
    assert summary["status_counts"]["failed"] == 1
    assert summary["status_counts"]["cancelled"] == 1
    assert summary["status_counts"]["pending"] == 1
    assert summary["progress_percent"] == 25.0
    assert summary["has_failures"] is True
    assert summary["is_all_completed"] is False
    assert summary["nodes"]["t2"]["error"] == "Fatal error"


def test_build_novel_generation_dag_structure():
    """Test that build_novel_generation_dag configures timeouts, retries, and dependencies."""
    graph = build_novel_generation_dag(book_id=42, ep_num=3)
    assert graph.dag_id == "novel_b42_ep3"
    assert len(graph.nodes) == 6

    write_node = graph.nodes["b42_ep3_write"]
    assert write_node.timeout_seconds == 300.0
    assert write_node.retry_limit == 2
    assert write_node.dependencies == ["b42_ep3_context"]

    illust_node = graph.nodes["b42_ep3_illust"]
    assert illust_node.resources.gpu_mem_mb == 2048
    assert illust_node.timeout_seconds == 120.0


@pytest.mark.asyncio
async def test_run_novel_dag_pipeline_async():
    """Test executing the novel DAG pipeline with mock tasks."""
    mock_registry = {
        "generate_plot_task": lambda **kwargs: {"plot": "epic outline"},
        "build_context_task": lambda **kwargs: {"context": "world details"},
        "write_chapter_task": lambda **kwargs: {"text": "Once upon a time..."},
        "audit_specialist_task": lambda **kwargs: {"score": 95},
        "illustration_task": lambda **kwargs: {"image_url": "http://example.com/img.png"},
        "publish_chapter_task": lambda **kwargs: {"saved": True},
    }

    summary = await run_novel_dag_pipeline_async(
        book_id=10,
        ep_num=1,
        task_registry=mock_registry,
        use_huey=False,
    )

    assert summary["total_nodes"] == 6
    assert summary["status_counts"]["completed"] == 6
    assert summary["progress_percent"] == 100.0
    assert summary["is_all_completed"] is True


def test_get_dag_status_endpoint():
    """Test the GET /api/tasks/dag/{dag_id} API endpoint."""
    client = TestClient(app)
    response = client.get("/api/tasks/dag/non_existent_dag_12345")
    assert response.status_code == 200
    data = response.json()
    assert data["dag_id"] == "non_existent_dag_12345"
    assert data["found"] is False


@pytest.mark.asyncio
async def test_resource_cleanup_on_exception():
    """Test that resources are cleaned up cleanly even if an exception escapes."""
    graph = DAGGraph(dag_id="test_cleanup_dag")
    node = DAGTaskNode(task_id="fail_node", func_name="exploding_fn", retry_limit=0)
    graph.add_node(node)

    def exploding_fn():
        raise RuntimeError("boom")

    scheduler = DAGScheduler(task_registry={"exploding_fn": exploding_fn})
    await scheduler.run_dag(graph)

    # Active allocations should be reset to 0
    assert scheduler.active_allocations.cpu_cores == 0.0
    assert scheduler.active_allocations.ram_mb == 0
    assert scheduler.active_allocations.gpu_mem_mb == 0
