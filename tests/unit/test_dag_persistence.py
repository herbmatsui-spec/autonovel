"""Tests for DAG Persistence (Step 6)."""
import pytest
import tempfile
from src.backend.tasks.dag_persistence import FileSystemDAGPersistence, DAGPersistence
from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode


@pytest.fixture
def persistence():
    with tempfile.TemporaryDirectory() as d:
        yield FileSystemDAGPersistence(d)


def test_save_load_checkpoint(persistence: DAGPersistence):
    """チェックポイント保存と読み込み。"""
    g = DAGGraph(dag_id="test_dag")
    g.add_node(DAGTaskNode(task_id="t1", func_name="f", status="completed", result="ok"))
    g.add_node(DAGTaskNode(task_id="t2", func_name="f", status="pending"))
    
    persistence.save_checkpoint(g, "cp1")
    loaded = persistence.load_checkpoint("cp1")
    
    assert loaded is not None
    assert loaded.dag_id == "test_dag"
    assert loaded.nodes["t1"].status == "completed"
    assert loaded.nodes["t1"].result == "ok"
    assert loaded.nodes["t2"].status == "pending"


def test_list_checkpoints(persistence: DAGPersistence):
    """チェックポイント一覧取得。"""
    g = DAGGraph(dag_id="dag1")
    persistence.save_checkpoint(g, "cp1")
    persistence.save_checkpoint(g, "cp2")
    assert persistence.list_checkpoints("dag1") == ["cp1", "cp2"]
    assert persistence.list_checkpoints("dag2") == []


def test_delete_checkpoint(persistence: DAGPersistence):
    """チェックポイント削除。"""
    g = DAGGraph(dag_id="dag1")
    persistence.save_checkpoint(g, "cp1")
    assert persistence.load_checkpoint("cp1") is not None
    persistence.delete_checkpoint("cp1")
    assert persistence.load_checkpoint("cp1") is None


def test_load_nonexistent_checkpoint(persistence: DAGPersistence):
    """存在しないチェックポイントは None を返す。"""
    assert persistence.load_checkpoint("nonexistent") is None


def test_resume_from_checkpoint():
    """チェックポイントからの復元 (resume_from 機能のシミュレーション)。"""
    with tempfile.TemporaryDirectory() as d:
        persistence = FileSystemDAGPersistence(d)
        g = DAGGraph(dag_id="resume_test")
        g.add_node(DAGTaskNode(task_id="t1", func_name="f", status="completed"))
        persistence.save_checkpoint(g, "resume_cp")
        
        # 新しいスケジューラで復元
        loaded = persistence.load_checkpoint("resume_cp")
        assert loaded.dag_id == "resume_test"
        assert loaded.nodes["t1"].status == "completed"


def test_scheduler_checkpoint_integration():
    """DAGScheduler のチェックポイント機能統合テスト。"""
    from src.backend.tasks.dag_scheduler import DAGScheduler
    
    with tempfile.TemporaryDirectory() as d:
        scheduler = DAGScheduler(
            persistence=FileSystemDAGPersistence(d),
            checkpoint_interval=2,  # 2タスクごと
        )
        
        def task_fn(task_id: str):
            return f"{task_id}_done"
        
        scheduler.register_task("task", task_fn)
        
        g = DAGGraph(dag_id="cp_integration_test")
        for i in range(4):
            g.add_node(DAGTaskNode(task_id=f"t{i}", func_name="task", kwargs={"task_id": f"t{i}"}))
        
        # 実行
        import asyncio
        completed = asyncio.run(scheduler.run_dag(g))
        
        assert completed.is_all_completed()
        
        # チェックポイントが作成されているか確認 (4タスク、interval=2 なので2回保存)
        checkpoints = scheduler.persistence.list_checkpoints("cp_integration_test")
        assert len(checkpoints) >= 1
        
        # 復元テスト
        latest_cp = scheduler.find_latest_checkpoint("cp_integration_test")
        assert latest_cp is not None
        
        recovered = scheduler.auto_recover("cp_integration_test")
        assert recovered is not None
        assert recovered.dag_id == "cp_integration_test"
        assert all(n.status == "completed" for n in recovered.nodes.values())