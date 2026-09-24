"""Unit tests for ConflictAlerter."""
import logging
from src.fusion.alerts import ConflictAlerter
from src.fusion.config import FusionConfig
from src.fusion.models import Conflict
from src.pipeline.emotional_residue import EmotionType


def test_alert_logs_warning(caplog):
    config = FusionConfig(alert_channels=["log"])
    alerter = ConflictAlerter(config)

    conflict = Conflict(
        pair=("A", "B"),
        emotion=EmotionType.FEAR,
        sources=[("annotation", 0.8, 1.0), ("pipeline", -0.5, 0.5)],
    )

    with caplog.at_level(logging.WARNING, logger="fusion.alerts"):
        res = alerter.alert([conflict], episode=15)

    assert res["status"] == "alerted"
    assert "Episode 15 detected 1 emotional conflicts" in caplog.text
    assert "A" in caplog.text
    assert "B" in caplog.text
