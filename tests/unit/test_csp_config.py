"""Unit tests for CSP config and structural constraints."""

import pytest
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import load_csp_config, CSPConfig
from src.narrative_balancer.csp.structural_constraints import StructuralConstraintBuilder
from src.narrative_balancer.csp.variables import CSPVariables


def test_csp_config_loading():
    cfg = load_csp_config("config/csp_balancer.yaml")
    assert cfg.n_episodes == 40
    assert cfg.midpoint_episode == 20
    assert cfg.midpoint_min_tension == 7
    assert cfg.weights.smoothness == 3


def test_structural_constraints_build():
    model = cp_model.CpModel()
    cfg = CSPConfig(n_episodes=20, midpoint_episode=10, midpoint_min_tension=7)
    vars = CSPVariables(model, n_episodes=20)
    builder = StructuralConstraintBuilder(cfg)
    builder.add_hard_constraints(model, vars)

    # Solve model with only structural constraints
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    # Midpoint tension must be >= 7
    assert solver.Value(vars.tension[9]) >= 7
