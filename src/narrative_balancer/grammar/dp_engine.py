"""Grammar DP analysis engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from src.narrative_balancer.grammar.beat_mapping import beat_to_terminal
from src.narrative_balancer.grammar.constraint_penalties import (
    char_neglect_penalty,
    payoff_decay_penalty,
    tension_monotony_penalty,
)
from src.narrative_balancer.grammar.cost_model import GrammarCostModel, load_cost_model
from src.narrative_balancer.grammar.dp import min_completion_cost
from src.narrative_balancer.grammar.parse_forest import ParseForest
from src.narrative_balancer.grammar.parser import EarleyParser
from src.narrative_balancer.grammar.symbols import NonTerminal
from src.narrative_balancer.models import Beat


@dataclass
class GrammarAnalysisResult:
    total_episodes: int
    pending_nonterminals: Set[NonTerminal]
    completion_cost: float
    penalties: Dict[str, float]
    total_cost: float
    is_valid_prefix: bool


class DPEngine:
    """Combines Earley partial parse and DP completion cost scoring."""

    def __init__(self, cost_model: GrammarCostModel = None):
        self.cost_model = cost_model or load_cost_model()
        self.parser = EarleyParser()

    def analyze(self, beats: List[Beat], target_total_episodes: int = 40) -> GrammarAnalysisResult:
        terminals = [beat_to_terminal(b) for b in beats]
        forest = self.parser.parse_prefix(terminals)

        remaining = max(0, target_total_episodes - len(beats))
        comp_cost = min_completion_cost(forest, remaining, self.cost_model)

        penalties = {
            "char_neglect": char_neglect_penalty(beats),
            "payoff_decay": payoff_decay_penalty(beats),
            "tension_monotony": tension_monotony_penalty(beats),
        }
        total_penalty = sum(penalties.values())
        total_cost = comp_cost + total_penalty

        return GrammarAnalysisResult(
            total_episodes=len(beats),
            pending_nonterminals=forest.pending_nonterminals,
            completion_cost=comp_cost,
            penalties=penalties,
            total_cost=total_cost,
            is_valid_prefix=forest.is_valid_prefix,
        )
