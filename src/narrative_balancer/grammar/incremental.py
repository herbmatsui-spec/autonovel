"""Incremental parser for step-by-step episode additions."""

from typing import List, Optional
from src.narrative_balancer.grammar.parser import EarleyParser
from src.narrative_balancer.grammar.parse_forest import ParseForest, EarleyItem
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal


class IncrementalParser:
    """Incrementally updates Earley chart upon receiving a new episode terminal."""

    def __init__(self, parser: Optional[EarleyParser] = None):
        self.parser = parser or EarleyParser()
        self.current_terminals: List[Terminal] = []
        self.current_forest: Optional[ParseForest] = None

    def reset(self):
        """Reset parser state."""
        self.current_terminals.clear()
        self.current_forest = None

    def add_terminal(self, terminal: Terminal) -> ParseForest:
        """Add one terminal and return updated ParseForest."""
        self.current_terminals.append(terminal)
        self.current_forest = self.parser.parse_prefix(self.current_terminals)
        return self.current_forest
