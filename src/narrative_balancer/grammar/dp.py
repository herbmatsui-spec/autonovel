"""Dynamic programming table and minimal completion cost calculator."""

from typing import Dict, List, Optional, Tuple, Union
import math
from src.narrative_balancer.grammar.cost_model import GrammarCostModel
from src.narrative_balancer.grammar.parse_forest import ParseForest
from src.narrative_balancer.grammar.rules import GRAMMAR, Production, Symbol
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal


class DPTable:
    """DP table mapping (Symbol, length) -> (min_cost, best_production, allocations)."""

    def __init__(self, cost_model: GrammarCostModel, max_len: int = 40):
        self.cost_model = cost_model
        self.max_len = max_len
        # (Symbol, length) -> (cost, chosen_production, list_of_sublengths)
        self.table: Dict[Tuple[Symbol, int], Tuple[float, Optional[Production], List[int]]] = {}

    def get_cost(self, sym: Symbol, length: int) -> float:
        return self.table.get((sym, length), (math.inf, None, []))[0]

    def set_entry(self, sym: Symbol, length: int, cost: float, prod: Optional[Production], alloc: List[int]):
        self.table[(sym, length)] = (cost, prod, alloc)


def build_dp_table(
    max_len: int = 40,
    cost_model: Optional[GrammarCostModel] = None,
    grammar: Optional[Dict[NonTerminal, List[Production]]] = None,
) -> DPTable:
    """Construct DP table for grammar expansion costs across remaining lengths."""
    costs = cost_model or GrammarCostModel()
    g = grammar or GRAMMAR
    dp = DPTable(costs, max_len)

    # Base cases: Terminals take length 1 with cost 0.0
    for term in Terminal:
        dp.set_entry(term, 1, 0.0, None, [1])
        for length in range(2, max_len + 1):
            dp.set_entry(term, length, math.inf, None, [])

    # Iteratively solve for nonterminals for length = 1..max_len
    # Since grammar DAG is stratified or short, we repeat passes
    for length in range(1, max_len + 1):
        for _ in range(3):  # Multi-pass for acyclic grammar propagation
            for nt, prods in g.items():
                best_cost, best_prod, best_alloc = dp.get_cost(nt, length), None, []
                current_min = best_cost

                for prod in prods:
                    m = len(prod)
                    if m == 0:
                        continue
                    if length < m:
                        continue

                    # Allocate lengths among symbols in prod
                    sub_cost, alloc = _min_partition(prod, length, dp)
                    total_cost = sub_cost + costs.rule_expansion_default
                    if total_cost < current_min:
                        current_min = total_cost
                        best_prod = prod
                        best_alloc = alloc

                if best_prod is not None:
                    dp.set_entry(nt, length, current_min, best_prod, best_alloc)

    return dp


def _min_partition(prod: Production, length: int, dp: DPTable) -> Tuple[float, List[int]]:
    """Helper to partition `length` among symbols in `prod` to minimize total cost."""
    m = len(prod)
    if m == 1:
        cost = dp.get_cost(prod[0], length)
        return cost, [length]

    # Dynamic programming for sequence of symbols in production
    # dp_seq[i][k] = min cost to allocate k episodes to first i symbols
    seq_table: Dict[Tuple[int, int], Tuple[float, List[int]]] = {}
    seq_table[(0, 0)] = (0.0, [])

    for i, sym in enumerate(prod, 1):
        for k in range(i, length + 1):
            best_cost = math.inf
            best_sub_alloc: List[int] = []

            for step in range(1, k - (i - 1) + 1):
                prev_cost, prev_alloc = seq_table.get((i - 1, k - step), (math.inf, []))
                sym_cost = dp.get_cost(sym, step)
                cand = prev_cost + sym_cost
                if cand < best_cost:
                    best_cost = cand
                    best_sub_alloc = prev_alloc + [step]

            if best_cost < math.inf:
                seq_table[(i, k)] = (best_cost, best_sub_alloc)

    return seq_table.get((m, length), (math.inf, []))


def min_completion_cost(
    forest: ParseForest,
    remaining_eps: int,
    cost_model: Optional[GrammarCostModel] = None,
) -> float:
    """Calculate minimal grammar completion cost given remaining episodes and forest."""
    costs = cost_model or GrammarCostModel()
    if remaining_eps <= 0:
        return 0.0 if not forest.pending_nonterminals else costs.get_penalty("missing_disaster")

    dp = build_dp_table(max_len=max(40, remaining_eps), cost_model=costs)

    if forest.pending_nonterminals:
        # Sum of minimum costs to complete pending nonterminals
        per_nt_len = max(1, remaining_eps // len(forest.pending_nonterminals))
        cost = 0.0
        for nt in forest.pending_nonterminals:
            c = dp.get_cost(nt, per_nt_len)
            cost += c if not math.isinf(c) else costs.rule_expansion_default * per_nt_len
        return cost
    else:
        # If no pending nonterminals, cost to expand STORY or QUARTER
        c = dp.get_cost(NonTerminal.QUARTER, remaining_eps)
        if not math.isinf(c):
            return c
        return costs.rule_expansion_default * remaining_eps


def reconstruct_optimal_expansion(
    dp: DPTable,
    root: Symbol,
    length: int,
) -> List[Terminal]:
    """Reconstruct sequence of terminals from DP table backtracking."""
    if isinstance(root, Terminal):
        return [root] * length

    entry = dp.table.get((root, length))
    if not entry or entry[1] is None:
        # Fallback to default linear progression
        return [Terminal.SETUP] + [Terminal.RISING] * max(0, length - 2) + [Terminal.CLIMAX]

    prod, alloc = entry[1], entry[2]
    result: List[Terminal] = []
    for sym, sub_len in zip(prod, alloc):
        result.extend(reconstruct_optimal_expansion(dp, sym, sub_len))

    return result
