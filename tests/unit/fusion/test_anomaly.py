"""Unit tests for anomaly detection."""
from src.fusion.anomaly import AnomalyDetector
from src.fusion.config import FusionConfig
from src.fusion.models import Conflict, FusedValue, FusedVector
from src.pipeline.emotional_residue import EmotionType


def test_conflict_spike_alert():
    config = FusionConfig()
    detector = AnomalyDetector(config)

    # 前話: 1件
    prev_fv = FusedVector()
    prev_fv.conflicts.append(Conflict(("A", "B"), EmotionType.FEAR, []))

    # 今話: 3件 (3 / 1 = 3.0 >= 2.0)
    curr_fv = FusedVector()
    curr_fv.conflicts.append(Conflict(("A", "B"), EmotionType.FEAR, []))
    curr_fv.conflicts.append(Conflict(("C", "D"), EmotionType.TRUST, []))
    curr_fv.conflicts.append(Conflict(("E", "F"), EmotionType.TENSION, []))

    anomalies = detector.check_anomalies(curr_fv, prev_fv)
    spike_alerts = [a for a in anomalies if a["type"] == "CONFLICT_SPIKE"]
    assert len(spike_alerts) == 1
    assert spike_alerts[0]["severity"] == "HIGH"


def test_annotation_stale_alert():
    config = FusionConfig()
    detector = AnomalyDetector(config)

    curr_fv = FusedVector()
    # 直近3話で annotation が含まれない
    recent_sources = [
        ["pipeline", "rule_engine"],
        ["pipeline"],
        ["rule_engine"],
    ]
    anomalies = detector.check_anomalies(curr_fv, recent_contributing_sources=recent_sources)
    stale_alerts = [a for a in anomalies if a["type"] == "ANNOTATION_STALE"]
    assert len(stale_alerts) == 1


def test_low_confidence_alert():
    config = FusionConfig()
    detector = AnomalyDetector(config)

    curr_fv = FusedVector()
    curr_fv.values[("A", "B", EmotionType.FEAR)] = FusedValue(0.5, "pipeline", confidence=0.3)
    curr_fv.values[("C", "D", EmotionType.TRUST)] = FusedValue(0.2, "pipeline", confidence=0.4)

    anomalies = detector.check_anomalies(curr_fv)
    low_conf_alerts = [a for a in anomalies if a["type"] == "LOW_AVG_CONFIDENCE"]
    assert len(low_conf_alerts) == 1
