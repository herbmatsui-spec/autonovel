"""Constraint builder base interface."""

from abc import ABC, abstractmethod
from typing import List
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.variables import CSPVariables


class ConstraintBuilder(ABC):
    """Abstract interface for building structural and quality constraints."""

    @abstractmethod
    def add_hard_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> None:
        """Add non-negotiable structural constraints to the CP-SAT model."""
        pass

    @abstractmethod
    def add_soft_constraints(self, model: cp_model.CpModel, vars: CSPVariables) -> List[cp_model.IntVar]:
        """Add optional quality penalties and return penalty terms to minimize."""
        pass
