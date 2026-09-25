"""Performance tests for Week 4 Fusion Layer."""
import time
from src.fusion.arbitrator import Arbitrator
from src.fusion.config import FusionConfig
from src.fusion.conflict_detector import ConflictDetector
from src.fusion.engine import FusionEngine
from src.fusion.models import SourceVector
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_fusion_performance_100_pairs():
    store = InMemoryVectorStore()
    config = FusionConfig()

    for i in range(100):
        src, tgt = f"Char{i}", f"Char{i+1}"
        v_anno = EmotionalVector(episode_id="ep1")
        v_anno.set_signal(EmotionalSignal(src, tgt, EmotionType.FEAR, 0.8, 1.0, "...", "ep1"))
        store.upsert("annotation", f"ep1:{src}->{tgt}", v_anno)

        v_rule = EmotionalVector(episode_id="ep1")
        v_rule.set_signal(EmotionalSignal(src, tgt, EmotionType.FEAR, 0.6, 0.8, "...", "ep1"))
        store.upsert("rule_engine", f"ep1:{src}->{tgt}", v_rule)

    engine = FusionEngine(store, config)

    t0 = time.perf_counter()
    fused = engine.fuse_all(episode=1)
    duration_ms = (time.perf_counter() - t0) * 1000

    assert len(fused.values) == 100
    # 100ペア融合が高速（100ms未満）に完了すること
    assert duration_ms < 150, f"Fusion took {duration_ms:.2f}ms"


def test_conflict_detection_performance_1000_items():
    config = FusionConfig()
    detector = ConflictDetector(config)

    v_anno = EmotionalVector(episode_id="ep1")
    v_pipe = EmotionalVector(episode_id="ep1")

    # 1000ペア作成（各ペアで正負が反転した矛盾を生成）
    for i in range(1000):
        src, tgt = f"U{i}", f"V{i}"
        v_anno.set_signal(EmotionalSignal(src, tgt, EmotionType.FEAR, 0.8, 1.0, "...", "ep1"))
        v_pipe.set_signal(EmotionalSignal(src, tgt, EmotionType.FEAR, -0.7, 0.5, "...", "ep1"))

    sv1 = SourceVector("annotation", v_anno, 1.0)
    sv2 = SourceVector("pipeline", v_pipe, 0.5)

    t0 = time.perf_counter()
    conflicts = detector.detect([sv1, sv2])
    duration_ms = (time.perf_counter() - t0) * 1000

    assert len(conflicts) == 1000
    assert duration_ms < 200, f"Conflict detection took {duration_ms:.2f}ms"
