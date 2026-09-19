"""CP-SAT solver invocation routines."""

from typing import Tuple
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.config import CSPConfig


def solve_csp(model: cp_model.CpModel, config: CSPConfig) -> Tuple[cp_model.CpSolver, int]:
    """Configure and invoke Google OR-Tools CP-SAT solver."""
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.solver.max_time_seconds
    solver.parameters.num_search_workers = config.solver.num_search_workers
    solver.parameters.log_search_progress = config.solver.log_search_progress

    status = solver.Solve(model)
    return solver, status
