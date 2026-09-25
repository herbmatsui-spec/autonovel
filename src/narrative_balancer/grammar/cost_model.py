"""Cost model for grammar expansion and structural alignment."""

from pathlib import Path
from typing import Dict, Optional, Union
import yaml
from pydantic import BaseModel, Field, ConfigDict
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal


class GrammarCostModel(BaseModel):
    """Cost weights for DP completion and rewrite scoring."""
    model_config = ConfigDict(extra="ignore")

    rule_expansion_default: float = 1.0
    terminal_insertion_default: float = 2.0
    terminal_deletion_default: float = 3.0
    terminal_substitution_default: float = 2.5

    penalties: Dict[str, float] = Field(default_factory=lambda: {
        "stagnation": 15.0,
        "missing_disaster": 25.0,
        "character_neglect": 8.0,
        "payoff_decay": 10.0,
        "tension_monotony": 12.0,
    })

    def get_penalty(self, key: str) -> float:
        return self.penalties.get(key, 0.0)


def load_cost_model(config_path: Optional[Union[str, Path]] = None) -> GrammarCostModel:
    """Load cost model from YAML configuration file."""
    if config_path is None:
        path = Path("config/grammar_cost.yaml")
        if not path.exists():
            return GrammarCostModel()
    else:
        path = Path(config_path)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return GrammarCostModel(**data)
