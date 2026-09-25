"""Main Grammar Narrative Balancer."""

from typing import List, Optional
from src.narrative_balancer.grammar.corrector import force_midpoint_correction
from src.narrative_balancer.grammar.cost_model import GrammarCostModel, load_cost_model
from src.narrative_balancer.grammar.dp_engine import DPEngine, GrammarAnalysisResult
from src.narrative_balancer.grammar.quarter_validator import validate_quarter_boundaries
from src.narrative_balancer.grammar.rewriter import GrammarRewriter
from src.narrative_balancer.models import Beat


class GrammarNarrativeBalancer:
    """Story balance optimizer using Context-Free Grammar and Dynamic Programming."""

    def __init__(self, cost_model: Optional[GrammarCostModel] = None):
        self.cost_model = cost_model or load_cost_model()
        self.dp_engine = DPEngine(cost_model=self.cost_model)
        self.rewriter = GrammarRewriter()

    def analyze_only(self, beats: List[Beat]) -> GrammarAnalysisResult:
        """Run structural parser and DP cost analysis on the given beats."""
        return self.dp_engine.analyze(beats)

    def balance(self, beats: List[Beat], target_total_episodes: int = 40) -> List[Beat]:
        """Balance beat sequence by applying grammatic rewrites and midpoint disaster injections."""
        if not beats:
            return []

        # 1. Apply pattern-based rewrite rules (e.g. STAGNATION -> MIDPOINT_DISASTER)
        rewritten_beats, _ = self.rewriter.apply_best_rewrites(beats)

        # 2. Check quarter boundaries (ensure Q2 has disaster/high tension turn)
        violations = validate_quarter_boundaries(rewritten_beats)
        if any("Quarter 2 lacks a midpoint crisis" in v for v in violations):
            mid_ep = target_total_episodes // 2
            rewritten_beats = force_midpoint_correction(rewritten_beats, ep=mid_ep)

        return rewritten_beats
