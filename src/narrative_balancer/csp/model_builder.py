"""CP-SAT model builder assembling variables, constraints, and partial state."""

from typing import List, Tuple
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.constraint_factory import build_all_constraints
from src.narrative_balancer.csp.partial_state import PartialPlotState
from src.narrative_balancer.csp.soft_constraints import (
    add_character_balance_penalty,
    add_quarter_target_penalty,
    add_smoothness_penalty,
)
from src.narrative_balancer.csp.variables import CSPVariables, BEAT_TYPE_MAP


def apply_partial_state(
    model: cp_model.CpModel,
    vars: CSPVariables,
    partial: PartialPlotState,
    as_hard_constraints: bool = True,
) -> None:
    """Fix or hint confirmed values from partial plot state."""
    for ep, beat in partial.confirmed_beats.items():
        idx = ep - 1
        if 0 <= idx < vars.n_episodes:
            t_val = int(round(max(1.0, min(10.0, beat.tension))))
            bt_val = BEAT_TYPE_MAP.get(beat.beat_type, 0)

            # Add hints for solver search guidance
            model.AddHint(vars.tension[idx], t_val)
            model.AddHint(vars.beat_type[idx], bt_val)

            if as_hard_constraints:
                model.Add(vars.tension[idx] == t_val)
                model.Add(vars.beat_type[idx] == bt_val)


def build_csp_model(
    partial: PartialPlotState,
    config: CSPConfig,
    characters: List[str] = None,
    enforce_confirmed: bool = True,
) -> Tuple[cp_model.CpModel, CSPVariables, List[cp_model.IntVar]]:
    """Build complete CP-SAT model with variables, hard constraints, and soft penalties."""
    model = cp_model.CpModel()
    chars = characters or ["Protagonist", "Rival", "Mentor"]
    vars = CSPVariables(model, n_episodes=partial.total_episodes, characters=chars)

    # 1. Hard constraints
    build_all_constraints(model, vars, config)

    # 2. Confirmed episode constraints / hints
    apply_partial_state(model, vars, partial, as_hard_constraints=enforce_confirmed)

    # 3. Soft constraints (penalties)
    penalties: List[cp_model.IntVar] = []
    penalties.extend(add_smoothness_penalty(model, vars, config.weights.smoothness))
    penalties.extend(add_character_balance_penalty(model, vars, config.weights.char_balance))
    penalties.extend(add_quarter_target_penalty(model, vars, config.weights.quarter_target))

    if penalties:
        model.Minimize(sum(penalties))

    return model, vars, penalties
