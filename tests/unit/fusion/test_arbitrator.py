"""Unit tests for Arbitrator."""
import pytest
from src.fusion.arbitrator import Arbitrator
from src.fusion.config import FusionConfig
from src.fusion.models import SourceVector
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType


def test_fuse_no_conflict():
    config = FusionConfig(
        source_confidence={"annotation": 1.0, "rule_engine": 0.8, "pipeline": 0.5},
        blend_weights={"annotation": 0.7, "rule_engine": 0.2, "pipeline": 0.1},
    )
    arbitrator = Arbitrator(config)

    vec_anno = EmotionalVector(episode_id="ep15")
    vec_anno.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.8, 1.0, "...", "ep15"))
    sv_anno = SourceVector("annotation", vec_anno, 1.0)

    vec_rule = EmotionalVector(episode_id="ep15")
    vec_rule.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.6, 0.8, "...", "ep15"))
    sv_rule = SourceVector("rule_engine", vec_rule, 0.8)

    fused = arbitrator.fuse([sv_anno, sv_rule])
    assert len(fused.conflicts) == 0
    val = fused.get_value("A", "B", EmotionType.AFFECTION)
    assert val is not None
    assert val.value == 0.8  # annotation wins
    assert val.primary_source == "annotation"
    assert val.confidence == 1.0


def test_fuse_with_conflict_blend():
    config = FusionConfig(
        source_confidence={"annotation": 1.0, "pipeline": 0.5},
        blend_weights={"annotation": 0.7, "pipeline": 0.3},
        conflict_threshold=0.3,
        significance_threshold=0.3,
        conflict_penalty=0.2,
        mode="weighted_blend",
    )
    arbitrator = Arbitrator(config)

    # 矛盾する2つのシグナル
    vec_anno = EmotionalVector(episode_id="ep15")
    vec_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep15"))
    sv_anno = SourceVector("annotation", vec_anno, 1.0)

    vec_pipe = EmotionalVector(episode_id="ep15")
    vec_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.6, 0.5, "...", "ep15"))
    sv_pipe = SourceVector("pipeline", vec_pipe, 0.5)

    fused = arbitrator.fuse([sv_anno, sv_pipe])
    assert len(fused.conflicts) == 1
    val = fused.get_value("A", "B", EmotionType.FEAR)
    assert val is not None
    # 加重平均:
    # w_anno = 0.7 * 1.0 = 0.7
    # w_pipe = 0.3 * 0.5 = 0.15
    # val = (0.8 * 0.7 + (-0.6) * 0.15) / (0.7 + 0.15) = (0.56 - 0.09) / 0.85 = 0.47 / 0.85 =~ 0.5529
    assert 0.5 < val.value < 0.6
    # ペナルティ: 1.0 * (1 - 0.2) = 0.8
    assert pytest.approx(val.confidence, 0.01) == 0.8


def test_fuse_highest_confidence_mode():
    config = FusionConfig(
        source_confidence={"annotation": 1.0, "pipeline": 0.5},
        conflict_threshold=0.3,
        significance_threshold=0.3,
        conflict_penalty=0.2,
        mode="highest_confidence",
    )
    arbitrator = Arbitrator(config)

    vec_anno = EmotionalVector(episode_id="ep15")
    vec_anno.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep15"))
    sv_anno = SourceVector("annotation", vec_anno, 1.0)

    vec_pipe = EmotionalVector(episode_id="ep15")
    vec_pipe.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.6, 0.5, "...", "ep15"))
    sv_pipe = SourceVector("pipeline", vec_pipe, 0.5)

    fused = arbitrator.fuse([sv_anno, sv_pipe])
    val = fused.get_value("A", "B", EmotionType.FEAR)
    assert val is not None
    assert val.value == 0.8
    assert pytest.approx(val.confidence, 0.01) == 0.8
