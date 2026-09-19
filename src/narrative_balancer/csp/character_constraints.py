"""Character arc and presence constraints for CP-SAT."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.constraints import ConstraintBuilder
from src.narrative_balancer.csp.variables import CSPVariables


class CharacterArcConstraintBuilder(ConstraintBuilder):
    """Controls defeat pacing and character appearances."""

    def __init__(self, config: CSPConfig):
        self.config = config

    def add_hard_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> None:
        n = vars.n_episodes

        # Protagonist defeat count constraints
        model.Add(sum(vars.defeat) >= self.config.min_defeats)
        model.Add(sum(vars.defeat) <= self.config.max_defeats)

        # Character appearance constraints: Each character must appear at least 20% of episodes
        min_appearances = max(1, n // 5)
        for ch, presence_list in vars.char_presence.items():
            model.Add(sum(presence_list) >= min_appearances)

    def add_soft_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> List[cp_model.IntVar]:
        return []
