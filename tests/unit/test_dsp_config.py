"""Unit tests for DSP config."""

from pathlib import Path
import pytest
from src.narrative_balancer.dsp.config import load_dsp_config
from src.narrative_balancer.dsp.models import DSPConfig


def test_load_default_dsp_config():
    cfg = load_dsp_config("config/dsp_balancer.yaml")
    assert isinstance(cfg, DSPConfig)
    assert cfg.window_size == 8
    assert cfg.flatness_threshold == 0.60
    assert cfg.impulse.peak == 9.0


def test_load_nonexistent_config_raises():
    with pytest.raises(FileNotFoundError):
        load_dsp_config("nonexistent_path_xyz.yaml")
