"""Unit tests for ConflictDetector."""
from src.fusion.config import FusionConfig
from src.fusion.conflict_detector import ConflictDetector
from src.fusion.models import SourceVector
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType


def test_detect_sign_conflict():
    config = FusionConfig(
        conflict_threshold=0.3,
        significance_threshold=0.3,
    )
    detector = ConflictDetector(config)

    # 1. annotation: 信頼度 1.0, fear = 0.7
    vec_anno = EmotionalVector(episode_id="ep15")
    vec_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.7, 1.0, "...", "ep15"))
    sv_anno = SourceVector("annotation", vec_anno, 1.0)

    # 2. pipeline: 信頼度 0.5, fear = -0.5 (符号反転)
    vec_pipe = EmotionalVector(episode_id="ep15")
    vec_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.5, 0.5, "...", "ep15"))
    sv_pipe = SourceVector("pipeline", vec_pipe, 0.5)

    conflicts = detector.detect([sv_anno, sv_pipe])
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.pair == ("A", "B")
    assert conflict.emotion == EmotionType.FEAR
    assert len(conflict.sources) == 2


def test_no_conflict_same_sign():
    config = FusionConfig(conflict_threshold=0.3, significance_threshold=0.3)
    detector = ConflictDetector(config)

    vec1 = EmotionalVector(episode_id="ep15")
    vec1.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.8, 1.0, "...", "ep15"))
    sv1 = SourceVector("annotation", vec1, 1.0)

    vec2 = EmotionalVector(episode_id="ep15")
    vec2.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.4, 0.8, "...", "ep15"))
    sv2 = SourceVector("rule_engine", vec2, 0.8)

    conflicts = detector.detect([sv1, sv2])
    assert len(conflicts) == 0


def test_no_conflict_below_significance():
    config = FusionConfig(conflict_threshold=0.3, significance_threshold=0.3)
    detector = ConflictDetector(config)

    vec1 = EmotionalVector(episode_id="ep15")
    vec1.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.5, 1.0, "...", "ep15"))
    sv1 = SourceVector("annotation", vec1, 1.0)

    vec2 = EmotionalVector(episode_id="ep15")
    vec2.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, -0.1, 0.5, "...", "ep15"))
    sv2 = SourceVector("pipeline", vec2, 0.5)

    conflicts = detector.detect([sv1, sv2])
    assert len(conflicts) == 0
