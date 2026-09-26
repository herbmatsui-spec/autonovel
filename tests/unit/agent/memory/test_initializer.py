"""Unit tests for memory initializer."""
from src.agents.memory.initializer import initialize_memory_for_project
from src.stores.vector_store import InMemoryVectorStore


def test_init_new_project(tmp_path):
    store = InMemoryVectorStore()
    manager = initialize_memory_for_project(
        project_id="novel_test",
        branch="main",
        base_dir=tmp_path,
        vector_store=store,
    )
    assert manager is not None
    assert manager.core_memory is not None

    # 保存して再ロード
    manager.update_emotion("A", "B", "fear", 0.5)
    manager.save_state(tmp_path / "novel_test" / "main")

    manager2 = initialize_memory_for_project(
        project_id="novel_test",
        branch="main",
        base_dir=tmp_path,
        vector_store=store,
    )
    assert manager2.core_memory.character_emotions["A->B"]["fear"] == 0.5
