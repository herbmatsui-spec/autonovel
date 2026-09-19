"""Structural constraints for narrative milestones (Midpoint, All is lost, Climax)."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.constraints import ConstraintBuilder
from src.narrative_balancer.csp.variables import CSPVariables, BEAT_TYPE_MAP
from src.narrative_balancer.models import BeatType


class StructuralConstraintBuilder(ConstraintBuilder):
    """Enforces essential narrative milestones on the structural timeline."""

    def __init__(self, config: CSPConfig):
        self.config = config

    def add_hard_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> None:
        n = vars.n_episodes

        # Midpoint (e.g. Ep 20): High tension peak
        mid_idx = min(n - 1, self.config.midpoint_episode - 1)
        model.Add(vars.tension[mid_idx] >= self.config.midpoint_min_tension)

        # Midpoint beat should be disaster or battle/high impact
        mid_disaster_idx = BEAT_TYPE_MAP[BeatType.MIDPOINT_DISASTER]
        disaster_idx = BEAT_TYPE_MAP[BeatType.DISASTER]
        battle_idx = BEAT_TYPE_MAP[BeatType.BATTLE]
        model.AddAllowedAssignments(
            [vars.beat_type[mid_idx]],
            [[mid_disaster_idx], [disaster_idx], [battle_idx]],
        )

        # All is Lost (e.g. Ep 30 if n >= 30): Trough
        if n >= self.config.all_is_lost_episode:
            lost_idx = self.config.all_is_lost_episode - 1
            model.Add(vars.tension[lost_idx] <= self.config.all_is_lost_max_tension)

        # Climax (final episode): Climax beat type and high tension
        climax_idx = n - 1
        model.Add(vars.tension[climax_idx] >= self.config.climax_min_tension)
        climax_type_idx = BEAT_TYPE_MAP[BeatType.CLIMAX]
        resolution_type_idx = BEAT_TYPE_MAP[BeatType.RESOLUTION]
        model.AddAllowedAssignments(
            [vars.beat_type[climax_idx]],
            [[climax_type_idx], [resolution_type_idx]],
        )

    def add_soft_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> List[cp_model.IntVar]:
        return []
