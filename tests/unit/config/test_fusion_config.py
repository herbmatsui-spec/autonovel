"""Tests for config/fusion.yaml loading."""
from pathlib import Path
import yaml
from src.fusion.config import load_fusion_config, reset_fusion_config


def test_load_confidence_defaults(tmp_path):
    config_file = Path("config/fusion.yaml")
    assert config_file.exists()

    reset_fusion_config()
    config = load_fusion_config(config_file)
    assert config.source_confidence["annotation"] == 1.0
    assert config.source_confidence["rule_engine"] == 0.8
    assert config.source_confidence["pipeline"] == 0.5
    assert config.conflict_threshold == 0.3
    assert config.significance_threshold == 0.3
    assert config.blend_weights["annotation"] == 0.7
