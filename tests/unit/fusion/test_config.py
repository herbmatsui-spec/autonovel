"""Unit tests for FusionConfig and environment variable overrides."""
import os
from src.fusion.config import load_fusion_config, reset_fusion_config, FusionConfig


def test_env_override(monkeypatch):
    reset_fusion_config()
    monkeypatch.setenv("FUSION_CONF_ANNOTATION", "0.95")
    monkeypatch.setenv("FUSION_MODE", "highest_confidence")
    monkeypatch.setenv("FUSION_CONFLICT_THRESHOLD", "0.45")

    config = load_fusion_config()
    assert config.source_confidence["annotation"] == 0.95
    assert config.mode == "highest_confidence"
    assert config.conflict_threshold == 0.45

    reset_fusion_config()


def test_singleton_behavior():
    reset_fusion_config()
    conf1 = load_fusion_config()
    conf2 = load_fusion_config()
    assert conf1 is conf2
    reset_fusion_config()
