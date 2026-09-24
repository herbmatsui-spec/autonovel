"""Unit tests for fusion data models."""
from datetime import datetime, timezone
from src.fusion.models import SourceVector, FusedValue, Conflict, FusedVector
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType


def test_fused_value_creation():
    val = FusedValue(
        value=0.75,
        primary_source="annotation",
        contributing_sources=["annotation", "rule_engine"],
        confidence=0.9,
    )
    assert val.value == 0.75
    assert val.primary_source == "annotation"
    assert "rule_engine" in val.contributing_sources
    assert val.confidence == 0.9

    data = val.to_dict()
    restored = FusedValue.from_dict(data)
    assert restored.value == val.value
    assert restored.primary_source == val.primary_source
    assert restored.contributing_sources == val.contributing_sources
    assert restored.confidence == val.confidence


def test_source_vector_creation():
    vec = EmotionalVector(episode_id="ep15")
    vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "betrayal span", "ep15", "betrayal"))
    source_vec = SourceVector(
        namespace="annotation",
        vector=vec,
        confidence=1.0,
    )
    assert source_vec.namespace == "annotation"
    assert source_vec.confidence == 1.0
    assert source_vec.vector.episode_id == "ep15"

    data = source_vec.to_dict()
    restored = SourceVector.from_dict(data)
    assert restored.namespace == source_vec.namespace
    assert restored.confidence == source_vec.confidence
    assert restored.vector.episode_id == "ep15"


def test_conflict_creation():
    conflict = Conflict(
        pair=("A", "B"),
        emotion=EmotionType.FEAR,
        sources=[("annotation", 0.8, 1.0), ("pipeline", -0.5, 0.5)],
    )
    assert conflict.pair == ("A", "B")
    assert conflict.emotion == EmotionType.FEAR
    assert len(conflict.sources) == 2
    assert conflict.conflict_id != ""

    data = conflict.to_dict()
    restored = Conflict.from_dict(data)
    assert restored.pair == conflict.pair
    assert restored.emotion == conflict.emotion
    assert restored.sources == conflict.sources
    assert restored.conflict_id == conflict.conflict_id


def test_fused_vector_serialization():
    fv = FusedVector()
    fv.values[("A", "B", EmotionType.FEAR)] = FusedValue(0.8, "annotation", ["annotation"], 1.0)
    conflict = Conflict(
        pair=("A", "B"),
        emotion=EmotionType.FEAR,
        sources=[("annotation", 0.8, 1.0), ("pipeline", -0.5, 0.5)],
    )
    fv.conflicts.append(conflict)
    fv.metadata["episode"] = 15

    data = fv.to_dict()
    restored = FusedVector.from_dict(data)
    assert restored.metadata["episode"] == 15
    assert len(restored.conflicts) == 1
    val = restored.get_value("A", "B", EmotionType.FEAR)
    assert val is not None
    assert val.value == 0.8
    assert val.primary_source == "annotation"
