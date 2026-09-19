"""Factory for assembling all CP-SAT constraint builders."""

from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.constraints import ConstraintBuilder
from src.narrative_balancer.csp.structural_constraints import StructuralConstraintBuilder
from src.narrative_balancer.csp.character_constraints import CharacterArcConstraintBuilder
from src.narrative_balancer.csp.payoff_constraints import PayoffConstraintBuilder
from src.narrative_balancer.csp.tension_constraints import TensionPhysicsConstraintBuilder
from src.narrative_balancer.csp.quarter_constraints import QuarterBalanceConstraintBuilder
from src.narrative_balancer.csp.variables import CSPVariables


def build_all_constraints(
    model: cp_model.CpModel,
    vars: CSPVariables,
    config: CSPConfig,
) -> List[ConstraintBuilder]:
    """Instantiate and apply all hard constraints onto the CP-SAT model."""
    builders: List[ConstraintBuilder] = [
        StructuralConstraintBuilder(config),
        CharacterArcConstraintBuilder(config),
        PayoffConstraintBuilder(config),
        TensionPhysicsConstraintBuilder(config),
        QuarterBalanceConstraintBuilder(config),
    ]

    for builder in builders:
        builder.add_hard_constraints(model, vars)

    return builders
