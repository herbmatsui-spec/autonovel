"""Unit and Integration Tests for DAG Scheduler (Step 44)."""
from __future__ import annotations

import asyncio
import pytest

from src.backend.tasks.dag_models import (
    DAGGraph,
    DAGTaskNode,
    TaskResourceRequirement,
)
from src.backend.tasks.dag_scheduler import DAGScheduler
from src.backend.tasks.resource_manager import ResourceManager
from src.backend.tasks.generation_tasks import build_novel_generation_dag


@pytest.mark.asyncio
async def test_scheduler_parallel_execution():
    """独立タスクが並行に実行され、全ノードが完了することの検証."""
    scheduler = DAGScheduler()

    # 模擬関数
    execution_order = []

    def task_a(val: int):
        execution_order.append(f"a_{val}")
        return val * 2

    def task_b(val: int):
        execution_order.append(f"b_{val}")
        return val + 10

    scheduler.register_task("task_a", task_a)
    scheduler.register_task("task_b", task_b)

    g = DAGGraph(dag_id="parallel_test")
    g.add_node(DAGTaskNode(task_id="t1", func_name="task_a", kwargs={"val": 5}))
    g.add_node(DAGTaskNode(task_id="t2", func_name="task_b", kwargs={"val": 3}))

    completed_graph = await scheduler.run_dag(g, max_concurrency=4)

    assert completed_graph.is_all_completed()
    assert completed_graph.nodes["t1"].result == 10
    assert completed_graph.nodes["t2"].result == 13
    assert len(execution_order) == 2


@pytest.mark.asyncio
async def test_scheduler_affinity_binding():
    """同一章（book_id & ep_num）のタスクが同一ワーカーアフィニティにバインドされることの検証 (Step 40)."""
    scheduler = DAGScheduler()

    def dummy_task(**kwargs):
        return "ok"

    scheduler.register_task("dummy", dummy_task)

    g = DAGGraph(dag_id="affinity_test")
    g.add_node(DAGTaskNode(
        task_id="ep1_write",
        func_name="dummy",
        kwargs={"book_id": 1, "ep_num": 1},
    ))
    g.add_node(DAGTaskNode(
        task_id="ep1_audit",
        func_name="dummy",
        kwargs={"book_id": 1, "ep_num": 1},
        dependencies=["ep1_write"],
    ))

    await scheduler.run_dag(g)

    assert g.is_all_completed()
    assert "1:1" in scheduler.worker_affinity_map
    worker_id = scheduler.worker_affinity_map["1:1"]
    assert worker_id.startswith("worker_")


@pytest.mark.asyncio
async def test_scheduler_retry_mechanism():
    """タスク失敗時に自動リトライが働き、上限以内で成功することの検証 (Step 42)."""
    scheduler = DAGScheduler()

    attempts = {"count": 0}

    def flaky_task():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("Temporary network timeout")
        return "recovered"

    scheduler.register_task("flaky", flaky_task)

    g = DAGGraph(dag_id="retry_test")
    g.add_node(DAGTaskNode(
        task_id="flaky_task",
        func_name="flaky",
        retry_limit=3,
    ))

    await scheduler.run_dag(g)

    assert g.is_all_completed()
    assert g.nodes["flaky_task"].status == "completed"
    assert g.nodes["flaky_task"].result == "recovered"
    assert g.nodes["flaky_task"].retry_count == 1


@pytest.mark.asyncio
async def test_scheduler_fine_grained_recovery():
    """障害発生時に成功先行ノードを維持し、失敗ノードと下流のみを局所リカバリすることの検証 (Step 42)."""
    scheduler = DAGScheduler()

    g = DAGGraph(dag_id="recovery_test")
    g.add_node(DAGTaskNode(task_id="plot", func_name="plot"))
    g.add_node(DAGTaskNode(task_id="write", func_name="write", dependencies=["plot"]))
    g.add_node(DAGTaskNode(task_id="illust", func_name="illust", dependencies=["write"]))
    g.add_node(DAGTaskNode(task_id="publish", func_name="publish", dependencies=["illust"]))

    # 模擬状態: plot と write は成功、illust で致命的失敗、publish は待機のまま
    g.mark_completed("plot", result="plot_data")
    g.mark_completed("write", result="write_data")
    g.mark_failed("illust", error="GPU out of memory")

    # リカバリ実行
    reset_tasks = scheduler.retry_failed_subgraph(g, "illust")

    # illust とその下流の publish のみリセットされ、plot と write は成功のまま
    assert reset_tasks == ["illust", "publish"]
    assert g.nodes["plot"].status == "completed"
    assert g.nodes["write"].status == "completed"
    assert g.nodes["illust"].status == "ready"
    assert g.nodes["publish"].status == "pending"


@pytest.mark.asyncio
async def test_build_novel_generation_dag_pipeline():
    """generation_tasks.py の 6ノード章生成DAGが完全実行されることの検証 (Step 43)."""
    scheduler = DAGScheduler()

    def make_handler(name: str):
        def handler(**kwargs):
            return f"{name}_done"
        return handler

    for fname in [
        "generate_plot_task",
        "build_context_task",
        "write_chapter_task",
        "audit_specialist_task",
        "illustration_task",
        "publish_chapter_task",
    ]:
        scheduler.register_task(fname, make_handler(fname))

    g = build_novel_generation_dag(book_id=1, ep_num=1)
    assert len(g.nodes) == 6

    completed_graph = await scheduler.run_dag(g, max_concurrency=4)

    assert completed_graph.is_all_completed()
    assert not completed_graph.has_failures()
    assert completed_graph.nodes["b1_ep1_publish"].status == "completed"
