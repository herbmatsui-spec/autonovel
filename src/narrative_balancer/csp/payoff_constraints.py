"""Foreshadowing setup and payoff constraints for CP-SAT."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.constraints import ConstraintBuilder
from src.narrative_balancer.csp.variables import CSPVariables, BEAT_TYPE_MAP
from src.narrative_balancer.models import BeatType


class PayoffConstraintBuilder(ConstraintBuilder):
    """Enforces that foreshadowing setup leads to payoff within allowed episode window."""

    def __init__(self, config: CSPConfig):
        self.config = config

    def add_hard_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> None:
        n = vars.n_episodes
        max_dist = self.config.max_payoff_distance

        # Link vars.setup and vars.payoff to beat_type
        setup_idx = BEAT_TYPE_MAP[BeatType.SETUP]
        payoff_idx = BEAT_TYPE_MAP[BeatType.PAYOFF]

        for i in range(n):
            model.Add(vars.beat_type[i] == setup_idx).OnlyEnforceIf(vars.setup[i])
            model.Add(vars.beat_type[i] != setup_idx).OnlyEnforceIf(vars.setup[i].Not())

            model.Add(vars.beat_type[i] == payoff_idx).OnlyEnforceIf(vars.payoff[i])
            model.Add(vars.beat_type[i] != payoff_idx).OnlyEnforceIf(vars.payoff[i].Not())

            # If setup[i] is true, there must be at least one payoff in [i + 1, min(n, i + max_dist + 1)]
            if i + 1 < n:
                window_end = min(n, i + max_dist + 1)
                payoffs_in_window = vars.payoff[i + 1:window_end]
                if payoffs_in_window:
                    # setup[i] => sum(payoffs_in_window) >= 1
                    model.Add(sum(payoffs_in_window) >= 1).OnlyEnforceIf(vars.setup[i])

    def add_soft_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> List[cp_model.IntVar]:
        return []
