"""Unit tests for fusion analytics."""
from src.fusion.analytics import analyze_source_contribution
from src.fusion.models import Conflict, FusedValue, FusedVector
from src.pipeline.emotional_residue import EmotionType


def test_contribution_analysis():
    # 2話分の履歴を作成
    fv1 = FusedVector()
    fv1.values[("A", "B", EmotionType.FEAR)] = FusedValue(0.8, "annotation", ["annotation"], 1.0)
    fv1.values[("A", "C", EmotionType.TENSION)] = FusedValue(0.4, "rule_engine", ["rule_engine"], 0.8)

    fv2 = FusedVector()
    fv2.values[("A", "B", EmotionType.FEAR)] = FusedValue(0.7, "annotation", ["annotation"], 1.0)
    fv2.values[("C", "A", EmotionType.AFFECTION)] = FusedValue(0.2, "pipeline", ["pipeline"], 0.5)
    fv2.conflicts.append(Conflict(("A", "D"), EmotionType.TRUST, [("annotation", 0.7, 1.0), ("pipeline", -0.5, 0.5)]))

    stats = analyze_source_contribution([fv1, fv2])
    assert stats["total_episodes"] == 2
    assert stats["total_values"] == 4
    # annotation: 2 / 4 = 0.5
    assert stats["adoption_rates"]["annotation"] == 0.5
    # rule_engine: 1 / 4 = 0.25
    assert stats["adoption_rates"]["rule_engine"] == 0.25
    # pipeline: 1 / 4 = 0.25
    assert stats["adoption_rates"]["pipeline"] == 0.25
    assert stats["conflict_stats"]["total_conflicts"] == 1
    assert stats["confidence_distribution"]["max"] == 1.0
    assert stats["confidence_distribution"]["min"] == 0.5
