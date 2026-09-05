"""Unit tests for all correctors."""

from __future__ import annotations

import pytest

from src.services.anti_ai.corrector import BaseCorrector, CorrectedText
from src.services.anti_ai.correction_pipeline import AntiAICorrector
from src.services.anti_ai.correctors import (
    DirectEmotionCorrector,
    GenericVocabularyCorrector,
    HedgingPatternsCorrector,
    SameStructureCorrector,
    TemplatePhrasesCorrector,
    TransitionOveruseCorrector,
    UniformParagraphCorrector,
)
from src.services.anti_ai.models import AICategory, Severity, ViolationSpan


class TestTransitionOveruseCorrector:
    def test_drops_redundant_transitions(self) -> None:
        corrector = TransitionOveruseCorrector()
        text = "しかし、朝が来た。しかし、昼が来た。しかし、夜が来た。"
        v1 = ViolationSpan(category=AICategory.TRANSITION_OVERUSE, start=0, end=3, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)
        v2 = ViolationSpan(category=AICategory.TRANSITION_OVERUSE, start=9, end=12, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)
        v3 = ViolationSpan(category=AICategory.TRANSITION_OVERUSE, start=18, end=21, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1, v2, v3])
        assert result.changes == 2
        assert "しかし" in result.text
        assert result.text.count("しかし") == 1

    def test_keeps_first_transition(self) -> None:
        corrector = TransitionOveruseCorrector()
        text = "しかし、朝が来た。"
        v1 = ViolationSpan(category=AICategory.TRANSITION_OVERUSE, start=0, end=3, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 0
        assert "しかし" in result.text

    def test_no_violations(self) -> None:
        corrector = TransitionOveruseCorrector()
        text = "朝が来た。"
        result = corrector.correct(text, [])
        assert result.text == text
        assert result.changes == 0


class TestSameStructureCorrector:
    def test_replaces_consecutive_past_tense(self) -> None:
        corrector = SameStructureCorrector()
        text = "彼は走った。彼女は笑った。兄は泣いた。"
        v1 = ViolationSpan(category=AICategory.SAME_STRUCTURE, start=6, end=10, matched_text="笑った。", severity=Severity.HIGH, suggestion=None)
        v2 = ViolationSpan(category=AICategory.SAME_STRUCTURE, start=13, end=17, matched_text="泣いた。", severity=Severity.HIGH, suggestion=None)

        result = corrector.correct(text, [v1, v2])
        assert result.changes >= 0

    def test_no_violations(self) -> None:
        corrector = SameStructureCorrector()
        text = "彼は走った。彼女は笑った。兄は叫んだ。"
        result = corrector.correct(text, [])
        assert result.text == text


class TestDirectEmotionCorrector:
    def test_replaces_thought_verbs(self) -> None:
        corrector = DirectEmotionCorrector()
        text = "私は悲しかったと思った。"
        v1 = ViolationSpan(category=AICategory.DIRECT_EMOTION, start=6, end=11, matched_text="と思った。", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 1
        assert "胸がざわついた" in result.text

    def test_no_matching_pattern(self) -> None:
        corrector = DirectEmotionCorrector()
        text = "彼は走った。"
        v1 = ViolationSpan(category=AICategory.DIRECT_EMOTION, start=3, end=5, matched_text="った", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 0


class TestHedgingPatternsCorrector:
    def test_replaces_hedging_with_direct(self) -> None:
        corrector = HedgingPatternsCorrector()
        text = "それは重要かもしれません。"
        v1 = ViolationSpan(category=AICategory.HEDGING_PATTERNS, start=6, end=14, matched_text="かもしれません", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 1

    def test_drops_uncertain_language(self) -> None:
        corrector = HedgingPatternsCorrector()
        text = "おそらく雨だろう。"
        v1 = ViolationSpan(category=AICategory.HEDGING_PATTERNS, start=0, end=3, matched_text="おそらく", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 1


class TestTemplatePhrasesCorrector:
    def test_drops_template_phrases(self) -> None:
        corrector = TemplatePhrasesCorrector()
        text = "重要なことは、これです。"
        v1 = ViolationSpan(category=AICategory.TEMPLATE_PHRASES, start=0, end=4, matched_text="重要な", severity=Severity.HIGH, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 1
        assert "重要な" not in result.text

    def test_keeps_non_template(self) -> None:
        corrector = TemplatePhrasesCorrector()
        text = "彼は走った。"
        v1 = ViolationSpan(category=AICategory.TEMPLATE_PHRASES, start=0, end=3, matched_text="彼は", severity=Severity.HIGH, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 0


class TestUniformParagraphCorrector:
    def test_returns_no_changes(self) -> None:
        corrector = UniformParagraphCorrector()
        text = "第一段落。第二段落。第三段落。"
        v1 = ViolationSpan(category=AICategory.UNIFORM_PARAGRAPH, start=0, end=15, matched_text="paragraph", severity=Severity.LOW, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 0


class TestGenericVocabularyCorrector:
    def test_replaces_generic_adjectives(self) -> None:
        corrector = GenericVocabularyCorrector()
        text = "それは素晴らしい一日だった。"
        v1 = ViolationSpan(category=AICategory.GENERIC_VOCABULARY, start=4, end=8, matched_text="素晴らしい", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 1
        assert "素晴らしい" not in result.text

    def test_no_matching_term(self) -> None:
        corrector = GenericVocabularyCorrector()
        text = "それは青い車だった。"
        v1 = ViolationSpan(category=AICategory.GENERIC_VOCABULARY, start=4, end=6, matched_text="青い", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.changes == 0


class TestAntiAICorrectorPipeline:
    def test_applies_all_correctors(self) -> None:
        corrector = AntiAICorrector()

        text = "しかし、朝が来た。しかし、昼が来た。"
        v1 = ViolationSpan(category=AICategory.TRANSITION_OVERUSE, start=0, end=3, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)
        v2 = ViolationSpan(category=AICategory.TRANSITION_OVERUSE, start=9, end=12, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1, v2])
        assert result.total_changes == 1
        assert AICategory.TRANSITION_OVERUSE in result.category_changes

    def test_empty_violations(self) -> None:
        corrector = AntiAICorrector()
        text = "ただの文章。"
        result = corrector.correct(text, [])
        assert result.total_changes == 0
        assert result.text == text

    def test_filters_wrong_category(self) -> None:
        corrector = AntiAICorrector()
        text = "しかし、朝が来た。"
        v1 = ViolationSpan(category=AICategory.DIRECT_EMOTION, start=0, end=3, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        assert result.total_changes == 0

    def test_to_dict(self) -> None:
        corrector = AntiAICorrector()
        text = "しかし、朝が来た。"
        v1 = ViolationSpan(category=AICategory.TRANSITION_OVERUSE, start=0, end=3, matched_text="しかし", severity=Severity.MEDIUM, suggestion=None)

        result = corrector.correct(text, [v1])
        d = result.to_dict()
        assert "text_length" in d
        assert "total_changes" in d
        assert "category_changes" in d
