"""Unit tests for memory interfaces and basic CRUD."""
from src.agent.memory.interfaces import MemoryEntry, WorkingFrame
from src.agent.memory.core_memory import CoreMemory


def test_core_memory_crud():
    mem = CoreMemory()
    mem.set("test_key", "test_value")
    assert mem.get("test_key") == "test_value"
    assert mem.get("non_existing", "default") == "default"

    dumped = mem.dump()
    assert dumped["test_key"] == "test_value"


def test_memory_entry_and_frame_serialization():
    entry = MemoryEntry(id="m1", content="Scene text", metadata={"ep": 1})
    data = entry.to_dict()
    restored_entry = MemoryEntry.from_dict(data)
    assert restored_entry.id == "m1"
    assert restored_entry.content == "Scene text"
    assert restored_entry.metadata["ep"] == 1

    frame = WorkingFrame(scene_id=2, emotional_beats=[{"delta": 0.5}], plot_points=["climax"])
    frame_data = frame.to_dict()
    restored_frame = WorkingFrame.from_dict(frame_data)
    assert restored_frame.scene_id == 2
    assert len(restored_frame.emotional_beats) == 1
    assert restored_frame.plot_points == ["climax"]
