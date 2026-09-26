"""Unit tests for WorkingMemory."""
from src.agents.memory.archival_memory import ArchivalMemory
from src.agents.memory.interfaces import WorkingFrame
from src.agents.memory.working_memory import WorkingMemory
from src.stores.vector_store import InMemoryVectorStore


def test_frame_eviction_to_archival():
    store = InMemoryVectorStore()
    archival = ArchivalMemory(vector_store=store)
    working = WorkingMemory(max_frames=2, archival_memory=archival)

    f1 = WorkingFrame(scene_id=1, plot_points=["Start journey"], context_summary="Scene 1 begin")
    f2 = WorkingFrame(scene_id=2, plot_points=["Meet enemy"], context_summary="Scene 2 combat")
    f3 = WorkingFrame(scene_id=3, plot_points=["Victory"], context_summary="Scene 3 victory")

    working.push(f1)
    working.push(f2)
    assert len(working.get_frames()) == 2

    # 3つ目をプッシュ -> f1 が退避される
    working.push(f3)
    assert len(working.get_frames()) == 2
    assert working.peek().scene_id == 3

    # archival に f1 が保存されたか確認
    results = archival.search("Start journey")
    assert len(results) == 1
    assert "Scene 1" in results[0].content
