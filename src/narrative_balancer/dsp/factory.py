"""Factory for DSP Tension Balancer."""

from pathlib import Path
from typing import Optional, Union
from src.narrative_balancer.dsp.balancer import DSPTensionBalancer
from src.narrative_balancer.dsp.config import load_dsp_config
from src.narrative_balancer.dsp.models import DSPConfig


def create_dsp_balancer(config_path: Optional[Union[str, Path]] = None) -> DSPTensionBalancer:
    """Create a DSPTensionBalancer from a YAML config file or defaults."""
    if config_path is not None:
        cfg = load_dsp_config(config_path)
    else:
        # Check standard default config path
        default_file = Path("config/dsp_balancer.yaml")
        if default_file.exists():
            cfg = load_dsp_config(default_file)
        else:
            cfg = DSPConfig()

    return DSPTensionBalancer(config=cfg)
