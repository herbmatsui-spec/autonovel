"""Tension physics constraints for CP-SAT."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.constraints import ConstraintBuilder
from src.narrative_balancer.csp.variables import CSPVariables


class TensionPhysicsConstraintBuilder(ConstraintBuilder):
    """Enforces narrative physics: maximum tension jump and minimum momentum."""

    def __init__(self, config: CSPConfig, max_step_delta: int = 4):
        self.config = config
        self.max_step_delta = max_step_delta

    def add_hard_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> None:
        n = vars.n_episodes

        # Consecutive tension jumps cannot exceed max_step_delta (e.g. 4)
        for i in range(n - 1):
            diff = model.NewIntVar(-10, 10, f"diff_{i}")
            model.Add(diff == vars.tension[i + 1] - vars.tension[i])
            model.Add(diff <= self.max_step_delta)
            model.Add(diff >= -self.max_step_delta)

        # 3-episode rolling average >= 2 (sum of any 3 consecutive >= 6)
        for i in range(n - 2):
            model.Add(vars.tension[i] + vars.tension[i + 1] + vars.tension[i + 2] >= 6)

    def add_soft_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> List[cp_model.IntVar]:
        return []
