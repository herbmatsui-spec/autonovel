"""Unit tests for LLM bias correction utility."""

import pytest
import tempfile
import yaml
from pathlib import Path

# Import the module to access cache
import src.services.bias_correction as bc_module
from src.services.bias_correction import (
    load_bias_corrections,
    apply_bias_correction,
    compute_correction_factors_from_logs,
    save_correction_factors,
    DEFAULT_CORRECTIONS,
)


def reset_correction_cache():
    """Reset the global correction cache."""
    bc_module._correction_cache = None


class TestLoadBiasCorrections:
    def setup_method(self):
        reset_correction_cache()

    def test_load_default_config(self):
        """Test loading from default config file."""
        # Config file exists from Step 14
        corrections = load_bias_corrections("config/llm_bias_correction.yaml")
        assert isinstance(corrections, dict)
        assert len(corrections) == 8
        for spec in DEFAULT_CORRECTIONS:
            assert spec in corrections
            assert isinstance(corrections[spec], float)

    def test_load_missing_file_returns_defaults(self):
        """Test missing file returns defaults."""
        corrections = load_bias_corrections("nonexistent.yaml")
        assert corrections == DEFAULT_CORRECTIONS

    def test_caching(self):
        """Test that results are cached."""
        corrections1 = load_bias_corrections("config/llm_bias_correction.yaml")
        corrections2 = load_bias_corrections("config/llm_bias_correction.yaml")
        assert corrections1 is corrections2  # Same object due to caching


class TestApplyBiasCorrection:
    def setup_method(self):
        reset_correction_cache()

    def test_apply_correction_up(self):
        """Test correction factor > 1.0 increases score."""
        score = apply_bias_correction(70.0, "consistency")  # factor 1.02
        assert score == 71.4  # 70 * 1.02 = 71.4

    def test_apply_correction_down(self):
        """Test correction factor < 1.0 decreases score."""
        score = apply_bias_correction(80.0, "creativity")  # factor 0.98
        assert score == 78.4  # 80 * 0.98 = 78.4

    def test_apply_correction_neutral(self):
        """Test correction factor 1.0 leaves score unchanged."""
        score = apply_bias_correction(75.0, "reader_hook")  # factor 1.0
        assert score == 75.0

    def test_clip_at_100(self):
        """Test score clipped at 100."""
        score = apply_bias_correction(99.0, "consistency")  # 99 * 1.02 = 100.98 -> 100
        assert score == 100.0

    def test_clip_at_zero(self):
        """Test score clipped at 0."""
        score = apply_bias_correction(-10.0, "consistency")  # negative -> 0
        assert score == 0.0

    def test_unknown_specialist_defaults_to_neutral(self):
        """Test unknown specialist gets factor 1.0."""
        score = apply_bias_correction(70.0, "unknown_specialist")
        assert score == 70.0


class TestComputeCorrectionFactors:
    def setup_method(self):
        reset_correction_cache()

    def test_compute_from_logs(self):
        """Test computing factors from log entries."""
        logs = [
            {"specialist_name": "consistency", "score": 80.0, "confidence": 0.8},
            {"specialist_name": "consistency", "score": 82.0, "confidence": 0.9},
            {"specialist_name": "consistency", "score": 78.0, "confidence": 0.7},
            {"specialist_name": "consistency", "score": 81.0, "confidence": 0.85},
            {"specialist_name": "consistency", "score": 79.0, "confidence": 0.75},
            # Low confidence should be excluded
            {"specialist_name": "consistency", "score": 50.0, "confidence": 0.3},
            # Other specialist
            {"specialist_name": "creativity", "score": 70.0, "confidence": 0.8},
            {"specialist_name": "creativity", "score": 72.0, "confidence": 0.9},
            {"specialist_name": "creativity", "score": 68.0, "confidence": 0.7},
            {"specialist_name": "creativity", "score": 71.0, "confidence": 0.85},
            {"specialist_name": "creativity", "score": 69.0, "confidence": 0.75},
        ]

        factors = compute_correction_factors_from_logs(logs, target_median=75.0)

        assert "consistency" in factors
        assert "creativity" in factors
        # consistency median ~80, target 75 -> factor ~0.9375
        # creativity median ~70, target 75 -> factor ~1.071
        assert 0.9 < factors["consistency"] < 1.0
        assert 1.0 < factors["creativity"] < 1.2

    def test_insufficient_samples_returns_neutral(self):
        """Test insufficient samples returns neutral factor."""
        logs = [
            {"specialist_name": "consistency", "score": 80.0, "confidence": 0.8},
            {"specialist_name": "consistency", "score": 82.0, "confidence": 0.9},
            # Only 2 samples < 5 minimum
        ]

        factors = compute_correction_factors_from_logs(logs)
        assert factors["consistency"] == 1.0

    def test_all_specialists_present(self):
        """Test all 8 specialists present in output."""
        logs = []
        for spec in DEFAULT_CORRECTIONS:
            for i in range(5):
                logs.append({"specialist_name": spec, "score": 70.0 + i, "confidence": 0.8})

        factors = compute_correction_factors_from_logs(logs)
        for spec in DEFAULT_CORRECTIONS:
            assert spec in factors


class TestSaveCorrectionFactors:
    def setup_method(self):
        reset_correction_cache()

    def test_save_and_load_roundtrip(self):
        """Test saving and loading correction factors."""
        factors = {
            "consistency": 1.02,
            "creativity": 0.98,
            "reader_hook": 1.0,
            "emotion_curve": 1.01,
            "style": 0.99,
            "factual": 1.0,
            "structure": 1.03,
            "multimodal": 0.97,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = f.name

        try:
            save_correction_factors(factors, temp_path)
            loaded = load_bias_corrections(temp_path)
            assert loaded == factors
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])