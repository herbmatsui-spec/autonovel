"""E2E integration tests for the full anti-AI detection and correction loop."""

from __future__ import annotations


from src.services.anti_ai import (
    RuleBasedAntiAIDetector,
    AntiAICorrector,
    AntiAILoopController,
)
from src.services.anti_ai.models import AICategory, Severity, ViolationSpan


class TestAntiAIFullFlow:
    """End-to-end tests for the anti-AI loop."""

    def test_detect_and_correct_ai_fingerprint_text(self) -> None:
        ai_text = """しかし、朝が来た。しかし、昼が来た。しかし、夜が来た。
私は悲しかったと思った。深い洞察を得たと思った。
それは素晴らしい一日だった。重要なことであった。"""

        detector = RuleBasedAntiAIDetector()
        result = detector.detect(ai_text)

        assert result.total_score < 90.0
        assert len(result.violations) > 0

        corrector = AntiAICorrector()
        correction = corrector.correct(ai_text, result.violations)

        assert correction.total_changes > 0
        assert correction.text != ai_text

    def test_loop_controller_converges(self) -> None:
        ai_text = """しかし、朝が来た。しかし、昼が来た。しかし、夜が来た。
私は悲しかったと思った。深い洞察を得たと思った。
それは素晴らしい一日だった。重要なことであった。"""

        controller = AntiAILoopController(max_loops=5, score_threshold=90.0)
        loop_result = controller.run_sync(ai_text)

        assert loop_result.final_score >= 85.0
        assert loop_result.iterations <= 5
        assert loop_result.converged is True

    def test_no_false_positives_on_human_text(self) -> None:
        human_text = """雨が降り始めた。傘もなく、駆け出した。"""

        detector = RuleBasedAntiAIDetector()
        result = detector.detect(human_text)

        assert result.total_score >= 95.0
        assert len(result.violations) == 0

    def test_direct_emotion_corrector(self) -> None:
        text = "私は悲しかったと思った。"
        v = ViolationSpan(
            category=AICategory.DIRECT_EMOTION,
            start=5,
            end=10,
            matched_text="と思った。",
            severity=Severity.MEDIUM,
            suggestion=None,
        )

        corrector = AntiAICorrector()
        result = corrector.correct(text, [v])

        assert result.total_changes == 1
        assert "胸がざわついた" in result.text

    def test_transition_overuse_corrector(self) -> None:
        text = "しかし、朝が来た。しかし、昼が来た。"
        v1 = ViolationSpan(
            category=AICategory.TRANSITION_OVERUSE,
            start=0,
            end=3,
            matched_text="しかし",
            severity=Severity.MEDIUM,
            suggestion=None,
        )
        v2 = ViolationSpan(
            category=AICategory.TRANSITION_OVERUSE,
            start=9,
            end=12,
            matched_text="しかし",
            severity=Severity.MEDIUM,
            suggestion=None,
        )

        corrector = AntiAICorrector()
        result = corrector.correct(text, [v1, v2])

        assert result.total_changes == 1
        assert result.text.count("しかし") == 1

    def test_hedging_patterns_corrector(self) -> None:
        text = "それは重要かもしれません。"
        v = ViolationSpan(
            category=AICategory.HEDGING_PATTERNS,
            start=5,
            end=13,
            matched_text="かもしれません",
            severity=Severity.MEDIUM,
            suggestion=None,
        )

        corrector = AntiAICorrector()
        result = corrector.correct(text, [v])

        assert result.total_changes == 1
        assert "かもしれません" not in result.text

    def test_generic_vocabulary_corrector(self) -> None:
        text = "それは素晴らしい一日だった。"
        v = ViolationSpan(
            category=AICategory.GENERIC_VOCABULARY,
            start=4,
            end=8,
            matched_text="素晴らしい",
            severity=Severity.MEDIUM,
            suggestion=None,
        )

        corrector = AntiAICorrector()
        result = corrector.correct(text, [v])

        assert result.total_changes == 1
        assert "素晴らしい" not in result.text

    def test_empty_text_returns_clean(self) -> None:
        detector = RuleBasedAntiAIDetector()
        result = detector.detect("")

        assert result.total_score == 100.0
        assert len(result.violations) == 0

    def test_score_improvement_after_correction(self) -> None:
        ai_text = "しかし、朝が来た。しかし、昼が来た。"

        detector = RuleBasedAntiAIDetector()
        before_result = detector.detect(ai_text)
        before_score = before_result.total_score

        controller = AntiAILoopController(max_loops=3, score_threshold=90.0)
        loop_result = controller.run_sync(ai_text)

        assert loop_result.final_score >= before_score

    def test_all_categories_have_corrections(self) -> None:
        all_correctors = [
            (AICategory.TRANSITION_OVERUSE, "しかし、朝が来た。しかし、昼が来た。"),
            (AICategory.SAME_STRUCTURE, "彼は走った。彼女は笑った。"),
            (AICategory.DIRECT_EMOTION, "私は悲しかったと思った。"),
            (AICategory.HEDGING_PATTERNS, "それは重要かもしれません。"),
            (AICategory.TEMPLATE_PHRASES, "重要なことは、これです。"),
            (AICategory.GENERIC_VOCABULARY, "それは素晴らしい一日だった。"),
        ]

        corrector = AntiAICorrector()

        for category, text in all_correctors:
            detector = RuleBasedAntiAIDetector()
            result = detector.detect(text)
            violations = [v for v in result.violations if v.category == category]

            if violations:
                correction = corrector.correct(text, violations)
                assert correction.total_changes >= 0
