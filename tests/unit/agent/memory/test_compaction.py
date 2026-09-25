"""Unit tests for CompactionPolicy."""
from src.agent.memory.archival_memory import ArchivalMemory
from src.agent.memory.compaction import CompactionPolicy
from src.agent.memory.core_memory import CoreMemory
from src.stores.vector_store import InMemoryVectorStore


def test_compact_old_emotions():
    core = CoreMemory()
    archival = ArchivalMemory(InMemoryVectorStore())
    policy = CompactionPolicy(max_tokens=20, stale_episode_threshold=5)

    # 1. 7話前 (ep1) に更新された古い感情
    core.update_emotion("OldA", "OldB", "fear", 0.5, reason="old", episode_label="ep1")
    # 2. 直近 (ep8) に更新された感情
    core.update_emotion("NewA", "NewB", "fear", 0.8, reason="recent", episode_label="ep8")

    # 現在話数 = 8 で圧縮実行
    result = policy.compact(core_memory=core, current_episode=8, archival_memory=archival)
    assert result["compacted"] is True
    assert "OldA->OldB" in result["evicted_emotions"]

    # Core から OldA->OldB は削除されている
    assert "OldA->OldB" not in core.character_emotions
    # 直近の NewA->NewB は保持されている
    assert "NewA->NewB" in core.character_emotions

    # Archival に退避されていること
    archived = archival.search("OldA->OldB")
    assert len(archived) == 1
