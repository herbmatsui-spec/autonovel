"""
Unit tests for YAML config loading (Step 6).
"""

import pytest
from pathlib import Path
from src.narrative.subtext_engine.engine import SubtextEngine


def test_config_load_from_yaml():
    config_path = Path("config/subtext_rules.yaml")
    assert config_path.exists()

    engine = SubtextEngine.from_yaml(config_path)
    rules = engine.registry.list_rules()
    assert len(rules) >= 5

    # Test processing with YAML-loaded engine
    block = engine.process_block(
        engine.registry.list_rules()[0].to_model() and
        __import__("src.narrative.subtext_engine.models", fromlist=["DialogueBlock"]).DialogueBlock(
            speaker="User", lines=["「ごめんなさい」"]
        )
    )
    assert block is not None


def test_config_fallback_on_missing_file():
    engine = SubtextEngine.from_yaml("nonexistent_config_file.yaml")
    rules = engine.registry.list_rules()
    assert len(rules) > 0  # Fell back to default rules cleanly
