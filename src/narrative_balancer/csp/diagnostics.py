"""Infeasibility diagnostics and human-readable conflict clause generation."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.models import ConflictClause
from src.narrative_balancer.csp.partial_state import PartialPlotState


def explain_infeasibility(
    partial_state: PartialPlotState,
    config: CSPConfig,
) -> List[ConflictClause]:
    """Diagnose potential conflicts between user's partial state and structural narrative rules."""
    conflicts: List[ConflictClause] = []

    mid_ep = config.midpoint_episode
    if mid_ep in partial_state.confirmed_beats:
        b = partial_state.confirmed_beats[mid_ep]
        if b.tension < config.midpoint_min_tension:
            conflicts.append(ConflictClause(
                constraint_name="MidpointDisasterTension",
                episodes=[mid_ep],
                description=f"Confirmed episode {mid_ep} has low tension ({b.tension}), but midpoint requires tension >= {config.midpoint_min_tension}.",
                suggested_relaxation="Raise tension or convert beat to MIDPOINT_DISASTER/BATTLE.",
            ))

    lost_ep = config.all_is_lost_episode
    if lost_ep in partial_state.confirmed_beats:
        b = partial_state.confirmed_beats[lost_ep]
        if b.tension > config.all_is_lost_max_tension:
            conflicts.append(ConflictClause(
                constraint_name="AllIsLostTrough",
                episodes=[lost_ep],
                description=f"Confirmed episode {lost_ep} has high tension ({b.tension}), but All-Is-Lost requires tension <= {config.all_is_lost_max_tension}.",
                suggested_relaxation="Lower tension or introduce protagonist defeat.",
            ))

    # Check consecutive tension jumps in confirmed beats
    sorted_eps = sorted(partial_state.confirmed_beats.keys())
    for i in range(len(sorted_eps) - 1):
        ep1, ep2 = sorted_eps[i], sorted_eps[i + 1]
        if ep2 == ep1 + 1:
            t1 = partial_state.confirmed_beats[ep1].tension
            t2 = partial_state.confirmed_beats[ep2].tension
            if abs(t2 - t1) > 4.0:
                conflicts.append(ConflictClause(
                    constraint_name="TensionPhysicsDelta",
                    episodes=[ep1, ep2],
                    description=f"Jump of {abs(t2 - t1):.1f} between Ep {ep1} and Ep {ep2} exceeds max allowed delta (4.0).",
                    suggested_relaxation="Smooth transition between episodes.",
                ))

    return conflicts
