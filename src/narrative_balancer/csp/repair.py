"""Minimal-change narrative repair engine using CP-SAT."""

import logging
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.converter import csp_solution_to_beats
from src.narrative_balancer.csp.model_builder import build_csp_model
from src.narrative_balancer.csp.partial_state import PartialPlotState
from src.narrative_balancer.csp.solver import solve_csp
from src.narrative_balancer.models import BeatType

logger = logging.getLogger(__name__)


def repair_midpoint_sag(
    current_state: PartialPlotState,
    config: CSPConfig,
) -> PartialPlotState:
    """Repair mid-story sag or complete missing plot episodes with minimal changes."""
    # Attempt 1: Enforce confirmed states strictly
    model, vars, _ = build_csp_model(current_state, config, enforce_confirmed=True)
    solver, status = solve_csp(model, config)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solved_beats = csp_solution_to_beats(solver, vars)
        return current_state.merge_solution(solved_beats)

    # Attempt 2: If infeasible, relax confirmed episodes that are stagnant/daily in middle quarter
    logger.warning("Strict plot constraints infeasible; relaxing mid-arc confirmed beats.")
    relaxed_confirmed = dict(current_state.confirmed_beats)
    midpoint = config.midpoint_episode

    # Remove fixed constraints around midpoint if they conflict with midpoint disaster
    for ep in list(relaxed_confirmed.keys()):
        if abs(ep - midpoint) <= 2:
            beat = relaxed_confirmed[ep]
            if beat.tension < config.midpoint_min_tension or beat.beat_type in (BeatType.DAILY, BeatType.STAGNATION):
                del relaxed_confirmed[ep]

    relaxed_state = PartialPlotState(
        total_episodes=current_state.total_episodes,
        confirmed_beats=relaxed_confirmed,
        unconfirmed_episodes=set(range(1, current_state.total_episodes + 1)) - set(relaxed_confirmed.keys()),
    )

    model2, vars2, _ = build_csp_model(relaxed_state, config, enforce_confirmed=True)
    solver2, status2 = solve_csp(model2, config)

    if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solved_beats = csp_solution_to_beats(solver2, vars2)
        return relaxed_state.merge_solution(solved_beats)

    # Fallback: Solve without hard-fixing confirmed states (only hints)
    model3, vars3, _ = build_csp_model(current_state, config, enforce_confirmed=False)
    solver3, status3 = solve_csp(model3, config)
    if status3 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solved_beats = csp_solution_to_beats(solver3, vars3)
        return current_state.merge_solution(solved_beats)

    raise RuntimeError("Unable to find feasible narrative resolution under current constraints.")
