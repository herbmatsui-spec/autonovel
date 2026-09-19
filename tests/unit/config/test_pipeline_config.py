"""Tests for pipeline configuration with emotional residue."""
from __future__ import annotations

import pytest
import yaml


class TestPipelineConfig:
    """パイプライン設定テスト"""

    def test_emotional_residue_config(self):
        """感情残基抽出設定が読み込めること"""
        with open("config/context_compression.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        assert "emotional_residue" in config
        er = config["emotional_residue"]
        assert er["enabled"] is True
        assert er["vector_namespace"] == "pipeline"
        assert er["nlp_model"] == "ja_ginza"
        assert er["character_dict_path"] == "config/characters.yaml"

    def test_config_structure(self):
        """全体構造の妥当性"""
        with open("config/context_compression.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 既存セクションが維持されていること
        assert "compression" in config
        assert config["compression"]["enabled"] is True
        assert "layer1_keyphrase" in config["compression"]
        assert "layer2_subgraph" in config["compression"]
        assert "layer3_abstraction" in config["compression"]
        assert "layer4_trimming" in config["compression"]