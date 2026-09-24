"""Integration tests for persisting fused emotional vectors."""
from src.fusion.config import FusionConfig
from src.fusion.engine import FusionEngine
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.conflict_store import ConflictStore
from src.stores.vector_store import InMemoryVectorStore


def test_fused_vector_stored(tmp_path):
    store = InMemoryVectorStore()
    conflict_file = tmp_path / "conflicts.jsonl"
    conflict_store = ConflictStore(conflict_file)
    config = FusionConfig()

    # 矛盾のあるシグナルを作成
    v_anno = EmotionalVector(episode_id="ep15")
    v_anno.set_signal(EmotionalSignal("A", "D", EmotionType.TRUST, 0.7, 1.0, "...", "ep15"))
    store.upsert("annotation", "ep15:A->D", v_anno)

    v_pipe = EmotionalVector(episode_id="ep15")
    v_pipe.set_signal(EmotionalSignal("A", "D", EmotionType.TRUST, -0.6, 0.5, "...", "ep15"))
    store.upsert("pipeline", "ep15:A->D", v_pipe)

    engine = FusionEngine(
        vector_store=store,
        config=config,
        conflict_store=conflict_store,
    )

    fused = engine.fuse_and_persist(episode=15)
    assert len(fused.conflicts) == 1

    # 1. 矛盾ストアに記録されているか
    recorded_conflicts = conflict_store.get_conflicts_by_episode(15)
    assert len(recorded_conflicts) == 1
    assert recorded_conflicts[0].pair == ("A", "D")

    # 2. fused ネームスペースに保存されているか
    fused_keys = store.get_namespace_keys("fused")
    assert "ep15" in fused_keys
    assert "ep15:A->D" in fused_keys

    # 3. get_fused から復元可能か
    restored = engine.get_fused(episode=15)
    assert restored is not None
    val = restored.get_value("A", "D", EmotionType.TRUST)
    assert val is not None
    assert val.primary_source == "annotation"
