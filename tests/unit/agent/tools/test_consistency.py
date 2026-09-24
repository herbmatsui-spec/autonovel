"""Unit tests for consistency tool."""
from src.agent.memory.core_memory import CoreMemory
from src.agent.tools.consistency_tool import check_emotional_consistency
from src.fusion.models import FusedValue, FusedVector
from src.pipeline.emotional_residue import EmotionType


def test_detect_large_divergence():
    core = CoreMemory()
    core.update_emotion("A", "B", "fear", 0.9)

    baseline = FusedVector()
    baseline.values[("A", "B", EmotionType.FEAR)] = FusedValue(0.2, "pipeline")

    # 差が 0.7 > 0.5 のため LARGE_DIVERGENCE 警告
    report = check_emotional_consistency(core, baseline, divergence_threshold=0.5)
    assert report["consistent"] is True  # エラーはなく警告のみ
    assert report["warnings_count"] == 1
    assert report["warnings"][0]["type"] == "LARGE_DIVERGENCE"


def test_detect_sign_conflict():
    core = CoreMemory()
    core.update_emotion("A", "B", "trust", 0.8)

    baseline = FusedVector()
    baseline.values[("A", "B", EmotionType.TRUST)] = FusedValue(-0.7, "pipeline")

    report = check_emotional_consistency(core, baseline)
    assert report["consistent"] is False
    assert report["errors_count"] == 1
    assert report["errors"][0]["type"] == "SIGN_FLIP_CONFLICT"
