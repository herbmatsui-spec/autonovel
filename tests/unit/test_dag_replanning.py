"""Unit tests for DAGReplanner (Part 5 / Step 54 / Checkpoint 9)."""

import asyncio
import pytest
from unittest.mock import MagicMock

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode
from src.backend.tasks.dag_replanning import DAGReplanningState, DAGReplanner


def build_sample_novel_dag() -> DAGGraph:
    """Build a sample DAG:
    plot_gen -> draft_gen -> [audit_eval, illustration_gen] -> epub_export
    """
    g = DAGGraph(dag_id="novel_workflow")

    g.add_node(DAGTaskNode(task_id="plot_gen", func_name="generate_plot", status="completed"))
    g.add_node(DAGTaskNode(task_id="draft_gen", func_name="generate_draft", dependencies=["plot_gen"], status="completed"))
    g.add_node(DAGTaskNode(task_id="audit_eval", func_name="run_audit", dependencies=["draft_gen"], status="completed"))
    g.add_node(DAGTaskNode(task_id="illustration_gen", func_name="generate_image", dependencies=["draft_gen"], status="running"))
    g.add_node(DAGTaskNode(task_id="epub_export", func_name="export_epub", dependencies=["audit_eval", "illustration_gen"], status="pending"))

    return g


def test_get_downstream_tasks():
    """Verify BFS traversal correctly collects all direct and indirect children."""
    g = build_sample_novel_dag()

    downstream_from_draft = DAGReplanner.get_downstream_tasks(g, "draft_gen", include_self=False)
    assert set(downstream_from_draft) == {"audit_eval", "illustration_gen", "epub_export"}

    downstream_from_audit = DAGReplanner.get_downstream_tasks(g, "audit_eval", include_self=False)
    assert set(downstream_from_audit) == {"epub_export"}

    downstream_from_epub = DAGReplanner.get_downstream_tasks(g, "epub_export", include_self=False)
    assert downstream_from_epub == []


def test_cancel_downstream_execution():
    """Verify running and ready tasks are safely cancelled."""
    g = build_sample_novel_dag()

    # Create a mock asyncio task
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False

    cancelled = DAGReplanner.cancel_downstream_execution(
        g,
        trigger_node_id="draft_gen",
        active_async_tasks={"illustration_gen": mock_task},
    )

    assert mock_task.cancel.called
    assert "illustration_gen" in cancelled
    assert g.nodes["illustration_gen"].status == "cancelled"


def test_plan_local_retry_and_reschedule():
    """Verify target node resets to pending, retry_count increments, and downstream resets."""
    g = build_sample_novel_dag()

    state = DAGReplanner.plan_local_retry(
        g,
        target_node_id="draft_gen",
        new_kwargs={"pdca_directives": "カタルシス強化"},
        reason="PDCA audit failed: reader_experience below threshold",
    )

    assert isinstance(state, DAGReplanningState)
    assert state.trigger_node_id == "draft_gen"
    assert g.nodes["draft_gen"].status == "pending"
    assert g.nodes["draft_gen"].retry_count == 1
    assert g.nodes["draft_gen"].kwargs.get("pdca_directives") == "カタルシス強化"

    # Downstream should be reset to pending
    assert g.nodes["audit_eval"].status == "pending"
    assert g.nodes["illustration_gen"].status == "pending"
    assert g.nodes["epub_export"].status == "pending"

    # Once draft_gen completes, downstream nodes become ready
    g.mark_completed("draft_gen", result="改善された新原稿")
    ready = g.get_ready_tasks()
    ready_ids = [t.task_id for t in ready]
    assert "audit_eval" in ready_ids
    assert "illustration_gen" in ready_ids
    assert "epub_export" not in ready_ids  # waiting for audit and illustration
