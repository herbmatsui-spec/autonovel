"""Unit tests for MemoryManager."""
from src.agent.memory.interfaces import MemoryEntry, WorkingFrame
from src.agent.memory.manager import MemoryManager


def test_get_emotional_context_fallback():
    manager = MemoryManager()

    # 1. 最初は空
    assert manager.get_emotional_context(("A", "B")) == {}

    # 2. Archival にのみエントリが存在する場合のフォールバック
    manager.archival_memory.insert(MemoryEntry(
        id="arch1",
        content="過去のAとBの出会いの記録",
        metadata={"pair": ["A", "B"]},
    ))
    res = manager.get_emotional_context(("A", "B"))
    assert res.get("fallback_source") == "archival"
    assert "過去のAとBの出会いの記録" in res.get("content", "")

    # 3. Core に更新されたら Core 優先で返ること
    manager.update_emotion("A", "B", "affection", 0.5, reason="初対面好印象")
    res_core = manager.get_emotional_context(("A", "B"))
    assert res_core.get("affection") == 0.5
    assert res_core.get("cause") == "初対面好印象"


def test_update_emotion_working_frame_integration():
    manager = MemoryManager()
    frame = WorkingFrame(scene_id=1, plot_points=["Scene 1 encounter"])
    manager.working_memory.push(frame)

    manager.update_emotion("Hero", "Villain", "tension", 0.7, reason="敵対遭遇")
    assert len(frame.emotional_beats) == 1
    beat = frame.emotional_beats[0]
    assert beat["source"] == "Hero"
    assert beat["target"] == "Villain"
    assert beat["emotion"] == "tension"
    assert beat["result_value"] == 0.7
