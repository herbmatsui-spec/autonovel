"""Configuration schema and loader for CSP Balancer."""

from pathlib import Path
from typing import Dict, Optional, Union
import yaml
from pydantic import BaseModel, Field, ConfigDict


class CSPWeightsConfig(BaseModel):
    smoothness: int = Field(default=3, ge=0)
    char_balance: int = Field(default=5, ge=0)
    quarter_target: int = Field(default=10, ge=0)


class CSPSolverSettings(BaseModel):
    max_time_seconds: float = Field(default=5.0, ge=0.1)
    num_search_workers: int = Field(default=4, ge=1)
    log_search_progress: bool = Field(default=False)


class CSPConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    n_episodes: int = Field(default=40, ge=4, le=100)
    midpoint_episode: int = Field(default=20, ge=1)
    midpoint_min_tension: int = Field(default=7, ge=1, le=10)
    all_is_lost_episode: int = Field(default=30, ge=1)
    all_is_lost_max_tension: int = Field(default=4, ge=1, le=10)
    climax_episode: int = Field(default=40, ge=1)
    climax_min_tension: int = Field(default=8, ge=1, le=10)

    min_defeats: int = Field(default=4, ge=0)
    max_defeats: int = Field(default=14, ge=0)
    max_payoff_distance: int = Field(default=15, ge=1)

    weights: CSPWeightsConfig = Field(default_factory=CSPWeightsConfig)
    solver: CSPSolverSettings = Field(default_factory=CSPSolverSettings)


def load_csp_config(config_path: Union[str, Path]) -> CSPConfig:
    """Load CSP balancer configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return CSPConfig(**data)
