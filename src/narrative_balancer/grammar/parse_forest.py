"""Data structures for parse forests and Earley items."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal


@dataclass(frozen=True)
class EarleyItem:
    """Represents an Earley chart item: lhs -> alpha . beta, origin."""
    lhs: NonTerminal
    rule: Tuple[Union[NonTerminal, Terminal], ...]
    dot: int
    origin: int

    @property
    def next_symbol(self) -> Optional[Union[NonTerminal, Terminal]]:
        if self.dot < len(self.rule):
            return self.rule[self.dot]
        return None

    @property
    def is_completed(self) -> bool:
        return self.dot >= len(self.rule)


@dataclass
class ParseForest:
    """Contains chart states and analyzed pending/completed structures."""
    consumed_terminals: int
    chart: List[Set[EarleyItem]] = field(default_factory=list)
    pending_nonterminals: Set[NonTerminal] = field(default_factory=set)
    completed_nonterminals: Set[NonTerminal] = field(default_factory=set)
    is_valid_prefix: bool = True
