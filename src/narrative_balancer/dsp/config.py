"""Configuration loader for DSP Balancer."""

from pathlib import Path
from typing import Union
import yaml
from src.narrative_balancer.dsp.models import DSPConfig


def load_dsp_config(config_path: Union[str, Path]) -> DSPConfig:
    """Load and validate DSP balancer configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return DSPConfig(**data)
