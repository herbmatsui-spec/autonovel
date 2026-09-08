"""E2E Integration Test for DAGScheduler + Huey Queue Execution (Step 66)."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode, TaskResourceRequirement
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.tasks.dag_persistence import FileSystemDAGPersistence


@pytest.mark.asyncio
async def test_dag_huey_orchestration_e2e(tmp_path):
    """Verify that DAGScheduler can execute a multi-stage pipeline via Huey with checkpoint persistence."""
    graph = DAGGraph(dag_id="e2e_huey_pipeline")

    node_plot = DAGTaskNode(
        task_id="plot",
        func_name="generate_plot",
        kwargs={"concept": "Reincarnation fantasy"},
        priority=10,
    )
    node_ctx = DAGTaskNode(
        task_id="context",
        func_name="build_context",
        kwargs={"details": "Magic academy"},
        dependencies=["plot"],
        priority=8,
    )
    node_write = DAGTaskNode(
        task_id="write",
        func_name="write_prose",
        kwargs={"words": 2000},
        dependencies=["context"],
        priority=6,
    )

    graph.add_node(node_plot)
    graph.add_node(node_ctx)
    graph.add_node(node_write)

    persistence = FileSystemDAGPersistence(base_dir=str(tmp_path / "checkpoints"))
    mock_huey = MagicMock()
    scheduler = DAGScheduler(
        huey_instance=mock_huey,
        persistence=persistence,
        checkpoint_interval=1,
        use_huey=True,
    )

    fake_results = {
        "plot": {"status": "completed", "plot_outline": "Act 1: Awakening"},
        "context": {"status": "completed", "context_summary": "Academy setting"},
        "write": {"status": "completed", "draft_text": "He opened his eyes in a new world."},
    }

    with patch("src.backend.tasks.huey.execute_agent_node_task") as mock_exec, \
         patch("src.backend.tasks.huey.async_wait_huey_result", new_callable=AsyncMock) as mock_wait:

        def fake_exec_call(func_name, kwargs, node_id):
            task_handle = MagicMock()
            task_handle.node_id = node_id
            return task_handle

        async def fake_wait_call(task_handle, timeout=60.0):
            return fake_results[task_handle.node_id]

        mock_exec.side_effect = fake_exec_call
        mock_wait.side_effect = fake_wait_call

        result_graph = await scheduler.run_dag(graph)

        assert result_graph.is_all_completed() is True
        assert result_graph.nodes["plot"].result == fake_results["plot"]
        assert result_graph.nodes["context"].result == fake_results["context"]
        assert result_graph.nodes["write"].result == fake_results["write"]

        # Verify checkpoints were persisted
        checkpoints = persistence.list_checkpoints("e2e_huey_pipeline")
        assert len(checkpoints) >= 1

        # Verify loading checkpoint
        loaded = persistence.load_checkpoint(checkpoints[-1])
        assert loaded is not None
        assert loaded.dag_id == "e2e_huey_pipeline"
        assert loaded.nodes["write"].status == "completed"
