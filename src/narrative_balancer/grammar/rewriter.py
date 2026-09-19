"""Grammar rewrite engine applying structural rewrite rules."""

from typing import List, Optional, Tuple
from src.narrative_balancer.grammar.beat_mapping import beat_to_terminal, terminal_to_beat
from src.narrative_balancer.grammar.rewrite_rules import REWRITE_RULES, RewriteRule
from src.narrative_balancer.grammar.symbols import Terminal
from src.narrative_balancer.models import Beat, CorrectionAction


class GrammarRewriter:
    """Engine for rewriting deficient beat sequences into valid grammar trees."""

    def __init__(self, rules: Optional[List[RewriteRule]] = None):
        self.rules = sorted(rules or REWRITE_RULES, key=lambda r: r.priority, reverse=True)

    def apply_best_rewrites(self, beats: List[Beat]) -> Tuple[List[Beat], List[CorrectionAction]]:
        """Scan beats, apply matching rewrite rules, and return updated beats with action logs."""
        if not beats:
            return [], []

        n = len(beats)
        terminals = [beat_to_terminal(b) for b in beats]
        new_beats = [b.model_copy(deep=True) for b in beats]
        actions: List[CorrectionAction] = []

        for rule in self.rules:
            m = len(rule.pattern)
            for i in range(n - m + 1):
                # Check pattern match
                if terminals[i:i + m] == rule.pattern:
                    # Check condition
                    if rule.condition is None or rule.condition(i, n):
                        # Apply replacement
                        for offset, rep_term in enumerate(rule.replacement):
                            target_ep = i + offset + 1
                            orig_beat = new_beats[i + offset]
                            updated_beat = terminal_to_beat(rep_term, target_ep)
                            updated_beat.title = orig_beat.title or updated_beat.title
                            new_beats[i + offset] = updated_beat
                            terminals[i + offset] = rep_term

                            actions.append(CorrectionAction(
                                episode=target_ep,
                                action_type="GRAMMAR_REWRITE",
                                target_field="beat_type",
                                original_value=orig_beat.beat_type.value,
                                new_value=updated_beat.beat_type.value,
                                reason=f"Applied rule {rule.name}",
                            ))

        return new_beats, actions
