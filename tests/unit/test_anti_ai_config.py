"""Tests for the anti-AI configuration loader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.config.anti_ai_config import (
    AntiAIConfig,
    DEFAULT_CONFIG_PATH,
    DetectorSettings,
    FeatureSettings,
    LLMSanityCheckSettings,
    LoopSettings,
    clear_cache,
    load_anti_ai_config,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_cache()
    yield
    clear_cache()


class TestDefaults:
    def test_bare_config_has_all_categories(self):
        cfg = AntiAIConfig()
        detector_names = (
            "TRANSITION_OVERUSE",
            "SAME_STRUCTURE",
            "DIRECT_EMOTION",
            "HEDGING_PATTERNS",
            "TEMPLATE_PHRASES",
            "UNIFORM_PARAGRAPH",
            "GENERIC_VOCABULARY",
        )
        for name in detector_names:
            assert hasattr(cfg.detectors, name)
        assert cfg.llm_sanity_check.enabled is False
        assert cfg.feature.enabled is True
        assert cfg.loop.max_iterations == 2
        assert cfg.loop.stop_threshold == 70.0

    def test_default_severity_must_be_valid(self):
        with pytest.raises(ValueError):
            AntiAIConfig(feature=FeatureSettings(default_severity="nope"))

    def test_severity_accepts_all_four_values(self):
        for s in ("low", "medium", "high", "critical"):
            cfg = AntiAIConfig(feature=FeatureSettings(default_severity=s))
            assert cfg.feature.default_severity == s


class TestLoader:
    def test_default_yaml_loads(self):
        cfg = load_anti_ai_config(apply_env=False)
        assert isinstance(cfg, AntiAIConfig)
        # Sanity: the shipped YAML bumps max_iterations to 2
        assert cfg.loop.max_iterations == 2
        assert cfg.detectors.GENERIC_VOCABULARY.density_per_1000 == 5.0
        assert cfg.detectors.SAME_STRUCTURE.consecutive_count == 3

    def test_default_path_points_at_shipped_yaml(self):
        assert DEFAULT_CONFIG_PATH.name == "anti_ai_config.yaml"
        assert DEFAULT_CONFIG_PATH.exists()

    def test_missing_yaml_falls_back_to_defaults(self, tmp_path):
        bogus = tmp_path / "does-not-exist.yaml"
        cfg = load_anti_ai_config(config_path=str(bogus), apply_env=False)
        assert isinstance(cfg, AntiAIConfig)
        assert cfg.loop.max_iterations == 2  # default

    def test_env_overrides_take_effect(self, monkeypatch):
        monkeypatch.setenv("ANTI_AI_LLM_ENABLED", "true")
        monkeypatch.setenv("ANTI_AI_MAX_LOOPS", "5")
        monkeypatch.setenv("ANTI_AI_THRESHOLD", "85.0")
        monkeypatch.setenv("ENABLE_ANTI_AI_LOOP", "false")
        cfg = load_anti_ai_config()
        assert cfg.llm_sanity_check.enabled is True
        assert cfg.loop.max_iterations == 5
        assert cfg.loop.stop_threshold == 85.0
        assert cfg.feature.enabled is False

    def test_env_can_re_enable_loop(self, monkeypatch):
        monkeypatch.setenv("ENABLE_ANTI_AI_LOOP", "true")
        cfg = load_anti_ai_config()
        assert cfg.feature.enabled is True

    def test_env_truthy_values(self, monkeypatch):
        for v in ("1", "true", "yes", "on", "TRUE", "Yes"):
            monkeypatch.setenv("ENABLE_ANTI_AI_LOOP", v)
            clear_cache()
            cfg = load_anti_ai_config()
            assert cfg.feature.enabled is True, f"value {v!r} should enable"

    def test_env_falsy_values(self, monkeypatch):
        for v in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("ENABLE_ANTI_AI_LOOP", v)
            clear_cache()
            cfg = load_anti_ai_config()
            assert cfg.feature.enabled is False, f"value {v!r} should disable"


class TestDetectorSettings:
    def test_transition_threshold_bounded(self):
        with pytest.raises(ValueError):
            TransitionOveruseSettings = __import__(
                "src.config.anti_ai_config", fromlist=["TransitionOveruseSettings"]
            ).TransitionOveruseSettings
            TransitionOveruseSettings(density_threshold=1.5)

    def test_same_structure_count_at_least_two(self):
        from src.config.anti_ai_config import SameStructureSettings

        with pytest.raises(ValueError):
            SameStructureSettings(consecutive_count=1)

    def test_weight_must_be_non_negative(self):
        from src.config.anti_ai_config import GenericVocabularySettings

        with pytest.raises(ValueError):
            GenericVocabularySettings(weight=-0.1)
