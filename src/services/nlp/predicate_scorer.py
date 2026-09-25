"""Predicate scorer for refining syntactic confidence and points (0-25)."""

import logging
import re
from typing import List

from src.models.predicate_match import PredicateAnalysisResult, PredicateMatch

logger = logging.getLogger(__name__)

# Patterns indicating negation of resolution in Japanese
NEGATION_PATTERN = re.compile(
    r"(?:ない|なかった|ぬ|ず|わけではない|とは言えない|できない|不可能)[。！？!?\s]*$"
)


class PredicateScorer:
    """Calculates granular syntax score for foreshadowing resolution."""

    @classmethod
    def calculate_score(cls, analysis_result: PredicateAnalysisResult) -> int:
        """
        Calculate score (0 to 25) based on matches and negation context.

        Args:
            analysis_result: Raw predicate analysis result

        Returns:
            syntax_score integer between 0 and 25
        """
        if not analysis_result.matches:
            return 0

        # Filter out matches where the predicate is negated
        valid_matches: List[PredicateMatch] = []
        for m in analysis_result.matches:
            # Check if sentence negates the predicate
            if NEGATION_PATTERN.search(m.sentence):
                # Negated resolution should not count as resolved
                logger.debug(f"Negated predicate ignored: {m.predicate} in sentence: {m.sentence}")
                continue
            valid_matches.append(m)

        if not valid_matches:
            return 0

        has_resolved = any(m.predicate_type == "resolved" for m in valid_matches)
        has_progressed = any(m.predicate_type == "progressed" for m in valid_matches)
        has_mention = any(m.predicate_type == "mention_only" for m in valid_matches)

        if has_resolved:
            # Highest confidence match determines score scaling
            max_conf = max(
                (m.confidence_score for m in valid_matches if m.predicate_type == "resolved"),
                default=1.0,
            )
            return int(round(25 * max_conf))
        elif has_progressed:
            max_conf = max(
                (m.confidence_score for m in valid_matches if m.predicate_type == "progressed"),
                default=1.0,
            )
            return int(round(15 * max_conf))
        elif has_mention:
            return 5

        return 0
