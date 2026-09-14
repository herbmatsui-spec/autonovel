import pytest
from src.backend.workflows.graph_state import WorkflowState, PlotNodeOutput


def test_workflow_state_initialization():
    """WorkflowStateの初期化とフィールバリデーションをテスト"""
    state = WorkflowState(
        book_id=123,
        ep_num=1,
        branch_id=456
    )
    assert state.book_id == 123
    assert state.ep_num == 1
    assert state.branch_id == 456
    assert state.context_alignment == {}
    assert state.blueprint == {}
    assert state.final_plot == {}
    assert state.audit_results == []
    assert state.is_consistent == True
    assert state.retry_count == 0
    assert state.max_retries == 3
    assert state.status == "pending"


def test_workflow_state_with_custom_values():
    """カスタム値でWorkflowStateを初期化するテスト"""
    state = WorkflowState(
        book_id=999,
        ep_num=5,
        branch_id=789,
        context_alignment={"key": "value"},
        blueprint={"chapter": 1},
        final_plot={"arc": "complete"},
        audit_results=[{"check": "passed"}],
        is_consistent=False,
        retry_count=2,
        max_retries=5,
        status="success"
    )
    assert state.book_id == 999
    assert state.ep_num == 5
    assert state.branch_id == 789
    assert state.context_alignment == {"key": "value"}
    assert state.blueprint == {"chapter": 1}
    assert state.final_plot == {"arc": "complete"}
    assert state.audit_results == [{"check": "passed"}]
    assert state.is_consistent == False
    assert state.retry_count == 2
    assert state.max_retries == 5
    assert state.status == "success"


def test_plot_node_output_creation():
    """PlotNodeOutputの作成をテスト"""
    output = PlotNodeOutput(
        status="completed",
        data={"result": "success"},
        error=None
    )
    assert output.status == "completed"
    assert output.data == {"result": "success"}
    assert output.error is None


def test_plot_node_output_with_error():
    """エラーありのPlotNodeOutputをテスト"""
    output = PlotNodeOutput(
        status="failed",
        data={},
        error="Something went wrong"
    )
    assert output.status == "failed"
    assert output.data == {}
    assert output.error == "Something went wrong"


def test_base_workflow_import():
    """BaseWorkflowがインポートできることをテスト（抽象クラスなのでインスタンス化はしない）"""
    from src.backend.workflows.base_workflow import BaseWorkflow
    # 抽象クラスなのでインスタンス化はできないことを確認
    assert BaseWorkflow.__abstractmethods__ == frozenset({'execute'})