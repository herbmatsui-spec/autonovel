"""Unit tests for FusionEngine."""
import pytest
from src.fusion.config import FusionConfig
from src.fusion.engine import FusionEngine
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_fuse_all_pairs():
    store = InMemoryVectorStore()
    config = FusionConfig(
        source_confidence={"annotation": 1.0, "rule_engine": 0.8, "pipeline": 0.5},
        blend_weights={"annotation": 0.7, "rule_engine": 0.2, "pipeline": 0.1},
    )

    # ペア1: A -> B (annotation & pipeline)
    v1_anno = EmotionalVector(episode_id="ep15")
    v1_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep15"))
    store.upsert("annotation", "ep15:A->B", v1_anno)

    v1_pipe = EmotionalVector(episode_id="ep15")
    v1_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.2, 0.5, "...", "ep15"))
    store.upsert("pipeline", "ep15:A->B", v1_pipe)

    # ペア2: B -> C (rule_engine のみ)
    v2_rule = EmotionalVector(episode_id="ep15")
    v2_rule.set_signal(EmotionalSignal("B", "C", EmotionType.TENSION, 0.4, 0.8, "...", "ep15"))
    store.upsert("rule_engine", "ep15:B->C", v2_rule)

    engine = FusionEngine(store, config)
    fused = engine.fuse_all(episode=15)

    assert fused.metadata["episode"] == 15
    # ペア A->B の fear
    val_ab = fused.get_value("A", "B", EmotionType.FEAR)
    assert val_ab is not None
    assert val_ab.primary_source == "annotation"
    assert pytest.approx(val_ab.value, 0.001) == 0.8

    # ペア B->C の tension
    val_bc = fused.get_value("B", "C", EmotionType.TENSION)
    assert val_bc is not None
    assert val_bc.primary_source == "rule_engine"
    assert pytest.approx(val_bc.value, 0.001) == 0.4
