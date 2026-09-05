"""Unit tests for DAG Models and Engine (Steps 35 & 36)."""
from __future__ import annotations

import pytest

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode
from src.backend.tasks.dag_engine import DAGEngine, DAGCycleError


def test_dag_linear_execution_order():
    """線形依存のトポロジカルソート検証."""
    g = DAGGraph(dag_id="linear_workflow")
    g.add_node(DAGTaskNode(task_id="plot", func_name="generate_plot"))
    g.add_node(DAGTaskNode(task_id="write", func_name="write_chapter"))
    g.add_node(DAGTaskNode(task_id="audit", func_name="audit_chapter"))

    g.add_dependency("write", "plot")
    g.add_dependency("audit", "write")

    order = DAGEngine.topological_sort(g)
    assert order == ["plot", "write", "audit"]

    stages = DAGEngine.get_execution_stages(g)
    assert stages == [["plot"], ["write"], ["audit"]]


def test_dag_parallel_branch_stages():
    """並列実行ブランチのステージ分割検証."""
    g = DAGGraph(dag_id="branching_workflow")
    # plot -> write -> (illustration, audit) -> publish
    g.add_node(DAGTaskNode(task_id="plot", func_name="plot"))
    g.add_node(DAGTaskNode(task_id="write", func_name="write"))
    g.add_node(DAGTaskNode(task_id="illust", func_name="illust", priority=10))
    g.add_node(DAGTaskNode(task_id="audit", func_name="audit", priority=5))
    g.add_node(DAGTaskNode(task_id="publish", func_name="publish"))

    g.add_dependency("write", "plot")
    g.add_dependency("illust", "write")
    g.add_dependency("audit", "write")
    g.add_dependency("publish", "illust")
    g.add_dependency("publish", "audit")

    stages = DAGEngine.get_execution_stages(g)
    assert len(stages) == 4
    assert stages[0] == ["plot"]
    assert stages[1] == ["write"]
    # Stage 2: illust と audit が並列（優先度高い illust が先頭）
    assert stages[2] == ["illust", "audit"]
    assert stages[3] == ["publish"]


def test_dag_cycle_detection():
    """循環依存検知時に DAGCycleError が発生することの検証."""
    g = DAGGraph(dag_id="cycle_workflow")
    g.add_node(DAGTaskNode(task_id="a", func_name="task_a"))
    g.add_node(DAGTaskNode(task_id="b", func_name="task_b"))
    g.add_node(DAGTaskNode(task_id="c", func_name="task_c"))

    g.add_dependency("b", "a")  # a -> b
    g.add_dependency("c", "b")  # b -> c
    g.add_dependency("a", "c")  # c -> a (循環!)

    with pytest.raises(DAGCycleError):
        DAGEngine.topological_sort(g)


def test_dag_missing_dependency_error():
    """存在しないタスクへの依存時に KeyError が発生することの検証."""
    g = DAGGraph(dag_id="invalid_workflow")
    g.add_node(DAGTaskNode(task_id="t1", func_name="task_1", dependencies=["non_existent"]))

    with pytest.raises(KeyError):
        DAGEngine.validate_dag(g)
