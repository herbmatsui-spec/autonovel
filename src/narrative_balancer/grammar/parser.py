"""Earley Parser implementation for narrative grammar prefix parsing."""

from typing import Dict, List, Optional, Set, Tuple, Union
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal
from src.narrative_balancer.grammar.rules import GRAMMAR, Production
from src.narrative_balancer.grammar.parse_forest import EarleyItem, ParseForest


class EarleyParser:
    """Earley parser with partial prefix parsing and pending nonterminal extraction."""

    def __init__(
        self,
        grammar: Optional[Dict[NonTerminal, List[Production]]] = None,
        start_symbol: NonTerminal = NonTerminal.STORY,
        max_items_per_chart: int = 300,
    ):
        self.grammar = grammar or GRAMMAR
        self.start_symbol = start_symbol
        self.max_items_per_chart = max_items_per_chart

    def parse_prefix(self, terminals: List[Terminal]) -> ParseForest:
        """Parse a sequence of terminals up to the current point in narrative."""
        n = len(terminals)
        chart: List[Set[EarleyItem]] = [set() for _ in range(n + 1)]

        # Initial state: predict from start symbol
        for prod in self.grammar.get(self.start_symbol, []):
            chart[0].add(EarleyItem(
                lhs=self.start_symbol,
                rule=tuple(prod),
                dot=0,
                origin=0,
            ))

        for k in range(n + 1):
            changed = True
            while changed:
                changed = False
                current_items = list(chart[k])

                # Prune if chart set grows excessively (Step 21 ambiguity management)
                if len(current_items) > self.max_items_per_chart:
                    current_items = current_items[:self.max_items_per_chart]

                for item in current_items:
                    next_sym = item.next_symbol

                    if next_sym is not None:
                        # 1. Prediction (if next_symbol is NonTerminal)
                        if isinstance(next_sym, NonTerminal):
                            for prod in self.grammar.get(next_sym, []):
                                new_item = EarleyItem(
                                    lhs=next_sym,
                                    rule=tuple(prod),
                                    dot=0,
                                    origin=k,
                                )
                                if new_item not in chart[k]:
                                    chart[k].add(new_item)
                                    changed = True

                    else:
                        # 2. Completion (item is completed: dot == len(rule))
                        for parent_item in chart[item.origin]:
                            if parent_item.next_symbol == item.lhs:
                                advanced_item = EarleyItem(
                                    lhs=parent_item.lhs,
                                    rule=parent_item.rule,
                                    dot=parent_item.dot + 1,
                                    origin=parent_item.origin,
                                )
                                if advanced_item not in chart[k]:
                                    chart[k].add(advanced_item)
                                    changed = True

            # 3. Scanning (consume terminal at input[k])
            if k < n:
                token = terminals[k]
                for item in chart[k]:
                    if item.next_symbol == token:
                        scanned_item = EarleyItem(
                            lhs=item.lhs,
                            rule=item.rule,
                            dot=item.dot + 1,
                            origin=item.origin,
                        )
                        chart[k + 1].add(scanned_item)

        # Determine pending and completed nonterminals
        pending: Set[NonTerminal] = set()
        completed: Set[NonTerminal] = set()

        last_chart = chart[n]
        is_valid = len(last_chart) > 0

        for item in last_chart:
            if item.is_completed:
                completed.add(item.lhs)
            elif isinstance(item.next_symbol, NonTerminal):
                pending.add(item.next_symbol)

        return ParseForest(
            consumed_terminals=n,
            chart=chart,
            pending_nonterminals=pending,
            completed_nonterminals=completed,
            is_valid_prefix=is_valid,
        )
