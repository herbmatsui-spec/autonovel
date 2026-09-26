"""Unit tests for CoreMemory token budget and persistence."""
from src.agents.memory.core_memory import CoreMemory
from src.fusion.models import FusedValue, FusedVector
from src.pipeline.emotional_residue import EmotionType


def test_token_budget_compaction():
    mem = CoreMemory()
    mem.relationship_dynamics["A-B"] = {
        "trust_trajectory": [0.1 * i for i in range(25)],  # 25件
    }
    mem.active_hooks.extend(["hook1", "hook2", "hook1"])

    tokens = mem.estimate_tokens()
    assert tokens > 0

    # 閾値を低めにして強制圧縮
    compacted = mem.compact_if_needed(max_tokens=10)
    assert compacted is True
    assert len(mem.relationship_dynamics["A-B"]["trust_trajectory"]) == 10
    assert len(mem.active_hooks) == 2  # 重複排除


def test_core_memory_persistence(tmp_path):
    mem = CoreMemory()
    mem.update_emotion("A", "B", "fear", 0.6, reason="betrayal", episode_label="ep14")
    mem.active_hooks.append("hook1")

    save_path = tmp_path / "core_memory.json"
    mem.save_to_disk(save_path)

    mem2 = CoreMemory()
    loaded = mem2.load_from_disk(save_path)
    assert loaded is True
    assert mem2.character_emotions["A->B"]["fear"] == 0.6
    assert mem2.character_emotions["A->B"]["cause"] == "betrayal"
    assert "hook1" in mem2.active_hooks


def test_load_fused_vector():
    fv = FusedVector()
    fv.values[("A", "B", EmotionType.FEAR)] = FusedValue(0.75, "annotation", ["annotation"], 1.0)

    mem = CoreMemory()
    mem.load_fused_vector(fv, episode_label="ep15")
    assert mem.character_emotions["A->B"]["fear"] == 0.75
    assert mem.character_emotions["A->B"]["primary_source"] == "annotation"
    assert mem.character_emotions["A->B"]["updated"] == "ep15"
