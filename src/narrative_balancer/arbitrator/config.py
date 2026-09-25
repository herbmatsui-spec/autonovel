"""Configuration loader for the Arbitrator layer."""

from pathlib import Path
from typing import Dict, List, Optional, Union
import yaml
from pydantic import BaseModel, Field, ConfigDict


class ArbitratorConfig(BaseModel):
    """Configuration options for global narrative arbitration."""
    model_config = ConfigDict(extra="ignore")

    priority_order: List[str] = Field(default_factory=lambda: ["grammar", "csp", "dsp"])
    enabled_balancers: Dict[str, bool] = Field(default_factory=lambda: {
        "grammar": True,
        "csp": True,
        "dsp": True,
    })
    fallback_chain: List[str] = Field(default_factory=lambda: ["grammar", "csp", "dsp"])
    timeout_seconds: float = 10.0
    validate_output: bool = True


def load_arbitrator_config(config_path: Optional[Union[str, Path]] = None) -> ArbitratorConfig:
    """Load Arbitrator configuration from YAML or defaults."""
    if config_path is None:
        path = Path("config/arbitrator.yaml")
        if not path.exists():
            return ArbitratorConfig()
    else:
        path = Path(config_path)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return ArbitratorConfig(**data)
