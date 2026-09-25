"""Converter from CP-SAT solution variables to domain Beat models."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.variables import CSPVariables, INV_BEAT_TYPE_MAP
from src.narrative_balancer.models import Beat, BeatType


def csp_solution_to_beats(solver: cp_model.CpSolver, vars: CSPVariables) -> List[Beat]:
    """Map solved CP-SAT decision variables into Beat sequence."""
    beats: List[Beat] = []

    for i in range(vars.n_episodes):
        ep = i + 1
        t_val = float(solver.Value(vars.tension[i]))
        bt_int = solver.Value(vars.beat_type[i])
        beat_type = INV_BEAT_TYPE_MAP.get(bt_int, BeatType.SETUP)
        is_def = bool(solver.Value(vars.defeat[i]))

        chars_present = [ch for ch, presence in vars.char_presence.items() if solver.Value(presence[i])]

        beats.append(Beat(
            episode=ep,
            tension=t_val,
            beat_type=beat_type,
            title=f"第{ep}話",
            summary=f"ビート: {beat_type.value}",
            characters=chars_present,
            is_defeat=is_def,
        ))

    return beats
