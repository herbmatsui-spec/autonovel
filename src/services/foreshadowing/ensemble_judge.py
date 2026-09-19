"""Ensemble judge integrating 3 non-LLM layers to reach final resolution decisions."""

import logging
from typing import Optional

from src.models.ensemble_foreshadowing import EnsembleJudgment, EnsembleScoreBreakdown
from src.models.predicate_match import PredicateAnalysisResult
from src.models.writing_metadata import ForeshadowingReport
from src.services.nlp.predicate_scorer import PredicateScorer

logger = logging.getLogger(__name__)


class EnsembleJudge:
    """Evaluates foreshadowing resolution using zero-LLM ensemble voting."""

    RESOLVED_THRESHOLD = 75
    PROGRESSED_THRESHOLD = 35

    @classmethod
    def evaluate(
        cls,
        foreshadowing_id: int,
        is_contracted: bool,
        metadata_report: Optional[ForeshadowingReport],
        syntax_analysis: Optional[PredicateAnalysisResult],
    ) -> EnsembleJudgment:
        """
        Evaluate resolution for a single foreshadowing item.

        Args:
            foreshadowing_id: ID of the foreshadowing item
            is_contracted: Whether this item was contracted in the episode beat sheet (35 pts)
            metadata_report: Report from LLM co-generation metadata (up to 40 pts)
            syntax_analysis: Syntactic predicate analysis result (up to 25 pts)

        Returns:
            EnsembleJudgment with breakdown, status, and rationale
        """
        # 1. Contract Score (35 pts)
        contract_score = 35 if is_contracted else 0

        # 2. Metadata Report Score (40 pts max)
        metadata_score = 0
        if metadata_report:
            if metadata_report.action == "resolved":
                metadata_score = 40
            elif metadata_report.action == "progressed":
                metadata_score = 20
            elif metadata_report.action == "mentioned_only":
                metadata_score = 0

        # 3. Syntax Score (25 pts max)
        syntax_score = 0
        if syntax_analysis:
            syntax_score = PredicateScorer.calculate_score(syntax_analysis)

        # Total score
        total_score = contract_score + metadata_score + syntax_score

        # Determine effective thresholds based on metadata availability
        has_metadata = metadata_report is not None
        resolved_threshold = cls.RESOLVED_THRESHOLD if has_metadata else 55
        progressed_threshold = cls.PROGRESSED_THRESHOLD if has_metadata else 15

        # Determine status
        if total_score >= resolved_threshold:
            status = "RESOLVED"
            should_reschedule = False
            rationale = (
                f"Resolved with ensemble consensus ({total_score} pts: "
                f"Contract={contract_score}, Metadata={metadata_score}, Syntax={syntax_score})"
            )
        elif total_score >= progressed_threshold:
            status = "PROGRESSED"
            should_reschedule = True
            rationale = (
                f"Progressed but not fully resolved ({total_score} pts: "
                f"Contract={contract_score}, Metadata={metadata_score}, Syntax={syntax_score})"
            )
        else:
            status = "PLANTED"
            should_reschedule = is_contracted  # If contracted but not addressed, must reschedule
            rationale = (
                f"Remains planted/unresolved ({total_score} pts: "
                f"Contract={contract_score}, Metadata={metadata_score}, Syntax={syntax_score})"
            )

        breakdown = EnsembleScoreBreakdown(
            contract_score=contract_score,
            metadata_score=metadata_score,
            syntax_score=syntax_score,
            total_score=total_score,
        )

        return EnsembleJudgment(
            foreshadowing_id=foreshadowing_id,
            status=status,
            score_breakdown=breakdown,
            rationale=rationale,
            should_reschedule=should_reschedule,
        )
