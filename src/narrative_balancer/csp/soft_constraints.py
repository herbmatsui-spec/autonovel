"""Soft constraints and linearization utilities for CP-SAT."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.variables import CSPVariables


def linearize_abs(model: cp_model.CpModel, expr, name: str) -> cp_model.IntVar:
    """Linearize |expr| using AddAbsEquality."""
    abs_var = model.NewIntVar(0, 1000, name)
    model.AddAbsEquality(abs_var, expr)
    return abs_var


def add_smoothness_penalty(
    model: cp_model.CpModel,
    vars: CSPVariables,
    weight: int = 3,
) -> List[cp_model.IntVar]:
    """Penalize rapid oscillations in tension between consecutive episodes."""
    if weight <= 0:
        return []

    penalties = []
    for i in range(vars.n_episodes - 1):
        diff = vars.tension[i + 1] - vars.tension[i]
        abs_diff = linearize_abs(model, diff, f"smooth_abs_{i}")
        if weight == 1:
            penalties.append(abs_diff)
        else:
            w_pen = model.NewIntVar(0, 1000, f"smooth_pen_{i}")
            model.Add(w_pen == abs_diff * weight)
            penalties.append(w_pen)

    return penalties


def add_character_balance_penalty(
    model: cp_model.CpModel,
    vars: CSPVariables,
    weight: int = 5,
) -> List[cp_model.IntVar]:
    """Penalize extreme disparity in character screen time."""
    if weight <= 0 or len(vars.characters) < 2:
        return []

    counts = [sum(vars.char_presence[ch]) for ch in vars.characters]
    max_count = model.NewIntVar(0, vars.n_episodes, "max_char_count")
    min_count = model.NewIntVar(0, vars.n_episodes, "min_char_count")
    model.AddMaxEquality(max_count, counts)
    model.AddMinEquality(min_count, counts)

    disparity = max_count - min_count
    w_pen = model.NewIntVar(0, 10000, "char_balance_pen")
    model.Add(w_pen == disparity * weight)
    return [w_pen]


def add_quarter_target_penalty(
    model: cp_model.CpModel,
    vars: CSPVariables,
    weight: int = 10,
) -> List[cp_model.IntVar]:
    """Penalize divergence from target progression: Q1~4, Q2~5, Q3~6, Q4~7."""
    if weight <= 0:
        return []

    targets = [4, 5, 6, 7]
    n = vars.n_episodes
    q_size = max(1, n // 4)
    penalties = []

    for q in range(4):
        q_start = q * q_size
        q_end = n if q == 3 else min(n, (q + 1) * q_size)
        q_len = q_end - q_start
        if q_len <= 0:
            continue

        q_sum = sum(vars.tension[q_start:q_end])
        target_sum = targets[q] * q_len
        diff = q_sum - target_sum
        abs_diff = linearize_abs(model, diff, f"q_target_abs_{q}")

        w_pen = model.NewIntVar(0, 10000, f"q_target_pen_{q}")
        model.Add(w_pen == abs_diff * weight)
        penalties.append(w_pen)

    return penalties
