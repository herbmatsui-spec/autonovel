"""Unit tests for VectorCollector."""
from src.fusion.collector import VectorCollector
from src.fusion.config import FusionConfig
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_collect_from_multiple_namespaces():
    store = InMemoryVectorStore()
    config = FusionConfig(
        source_confidence={
            "annotation": 1.0,
            "rule_engine": 0.8,
            "pipeline": 0.5,
        }
    )

    # 1. annotation namespace に追加
    vec_anno = EmotionalVector(episode_id="ep15")
    vec_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "evidence", "ep15", "betrayal"))
    store.upsert("annotation", "ep15:A->B", vec_anno)

    # 2. pipeline namespace に追加
    vec_pipe = EmotionalVector(episode_id="ep15")
    vec_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.2, 0.6, "evidence", "ep15", "subtle"))
    store.upsert("pipeline", "ep15:A->B", vec_pipe)

    collector = VectorCollector(store, config)
    collected = collector.collect_all(("A", "B"))

    assert len(collected) == 2
    namespaces = {s.namespace for s in collected}
    assert namespaces == {"annotation", "pipeline"}

    anno_s = next(s for s in collected if s.namespace == "annotation")
    assert anno_s.confidence == 1.0
    assert anno_s.vector.get_value("A", "B", EmotionType.FEAR) == 0.8

    pipe_s = next(s for s in collected if s.namespace == "pipeline")
    assert pipe_s.confidence == 0.5
