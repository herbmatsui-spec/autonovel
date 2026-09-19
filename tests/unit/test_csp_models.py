"""Unit tests for CSP models and variables."""

import pytest
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.models import (
    BeatType,
    CharRole,
    ConflictClause,
    ConstraintPriority,
)
from src.narrative_balancer.csp.variables import CSPVariables, BEAT_TYPE_MAP


def test_csp_models():
    assert BeatType.MIDPOINT_DISASTER == "MIDPOINT_DISASTER"
    assert CharRole.PROTAGONIST == "PROTAGONIST"
    assert ConstraintPriority.HARD == "HARD"

    clause = ConflictClause(
        constraint_name="TestConstraint",
        episodes=[20],
        description="Conflict in ep 20",
        suggested_relaxation="Relax midpoint",
    )
    assert clause.episodes == [20]


def test_csp_variables_creation():
    model = cp_model.CpModel()
    chars = ["Hero", "Villain"]
    vars = CSPVariables(model, n_episodes=10, characters=chars)

    assert len(vars.tension) == 10
    assert len(vars.beat_type) == 10
    assert len(vars.defeat) == 10
    assert "Hero" in vars.char_presence
    assert len(vars.char_presence["Hero"]) == 10
