from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.backend.workflows.base_workflow import BaseWorkflow
from src.backend.workflows.dag_builder import DefaultAutoWorkflowBuilder
from src.backend.workflows.graph_state import WorkflowState


def test_default_auto_workflow_dag_builder():
    """DefaultAutoWorkflowBuilder が正しいパイプラインノードを構築することを検証"""
    builder = DefaultAutoWorkflowBuilder()
    pipeline = builder.build()
    node_names = [node.name for node in pipeline._nodes]
    assert "init_context" in node_names
    assert "plan_generation" in node_names
    assert "episode_writing" in node_names
    assert "audit_and_validation" in node_names
    assert len(pipeline._nodes) == 4


def test_base_workflow_dependency_delegation():
    """BaseWorkflow がエンジンまたは明示的に渡されたサービスを正しく委譲・初期化することを検証"""
    mock_engine = MagicMock()
    mock_engine.writer = MagicMock()
    mock_engine.planner = MagicMock()

    class DummyWorkflow(BaseWorkflow):
        async def execute(self, *args, **kwargs):
            return "done"

    # engine からのフォールバック
    wf_from_engine = DummyWorkflow(engine=mock_engine)
    assert wf_from_engine.writing == mock_engine.writer
    assert wf_from_engine.planner == mock_engine.planner

    # 明示的サービスの優先注入
    custom_planner = MagicMock()
    wf_custom = DummyWorkflow(engine=mock_engine, planner=custom_planner)
    assert wf_custom.planner == custom_planner
    assert wf_custom.writing == mock_engine.writer


def test_workflow_state_transition():
    """WorkflowState の状態遷移と追跡を検証"""
    state = WorkflowState(book_id=1, ep_num=1, branch_id=10)
    assert state.status == "pending"
    assert state.retry_count == 0

    state.status = "in_progress"
    state.retry_count += 1
    state.blueprint = {"title": "Test Title"}
    state.audit_results.append({"score": 90, "passed": True})

    assert state.status == "in_progress"
    assert state.retry_count == 1
    assert state.blueprint["title"] == "Test Title"
    assert len(state.audit_results) == 1