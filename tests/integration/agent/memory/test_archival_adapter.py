"""Integration tests for ArchivalMemory adapter."""
from src.agents.memory.archival_memory import ArchivalMemory
from src.agents.memory.interfaces import MemoryEntry
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_search_scenes():
    store = InMemoryVectorStore()
    archival = ArchivalMemory(vector_store=store)

    entry1 = MemoryEntry("e1", "第14話の裏切り事件で、AはBに強い不信感を抱いた。")
    entry2 = MemoryEntry("e2", "第10話の夏祭りで、二人は手をつないで花火を見た。")
    archival.insert(entry1)
    archival.insert(entry2)

    results = archival.search_emotional_scenes("裏切り", k=1)
    assert len(results) == 1
    assert results[0].id == "e1"

    results2 = archival.search_emotional_scenes("花火", k=1)
    assert len(results2) == 1
    assert results2[0].id == "e2"


def test_insert_emotional_summary():
    store = InMemoryVectorStore()
    archival = ArchivalMemory(vector_store=store)

    v = EmotionalVector(episode_id="ep15")
    v.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep15"))

    entry = archival.insert_emotional_summary(15, "AがBに恐怖を覚えた決定的瞬間", v)
    assert entry.metadata["episode"] == 15
    assert "ep15:summary" in store.get_namespace_keys("archival")
