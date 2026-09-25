"""Quarter balance constraints for CP-SAT."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.constraints import ConstraintBuilder
from src.narrative_balancer.csp.variables import CSPVariables, BEAT_TYPE_MAP
from src.narrative_balancer.models import BeatType


class QuarterBalanceConstraintBuilder(ConstraintBuilder):
    """Enforces beat distribution across narrative quarters."""

    def __init__(self, config: CSPConfig):
        self.config = config

    def add_hard_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> None:
        n = vars.n_episodes
        q_size = max(3, n // 4)

        daily_idx = BEAT_TYPE_MAP[BeatType.DAILY]
        battle_idx = BEAT_TYPE_MAP[BeatType.BATTLE]

        for q in range(4):
            q_start = q * q_size
            q_end = n if q == 3 else min(n, (q + 1) * q_size)
            q_len = q_end - q_start
            if q_len < 3:
                continue

            # Limit daily beats to at most 50% of the quarter
            daily_bools = []
            for ep in range(q_start, q_end):
                is_daily = model.NewBoolVar(f"is_daily_{ep}")
                model.Add(vars.beat_type[ep] == daily_idx).OnlyEnforceIf(is_daily)
                model.Add(vars.beat_type[ep] != daily_idx).OnlyEnforceIf(is_daily.Not())
                daily_bools.append(is_daily)

            model.Add(sum(daily_bools) <= max(2, q_len // 2))

    def add_soft_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> List[cp_model.IntVar]:
        return []
