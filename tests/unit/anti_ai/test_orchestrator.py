"""Integration tests for the rule-based orchestrator."""

from __future__ import annotations

import asyncio

import pytest

from src.config.anti_ai_config import (
    AntiAIConfig,
    DetectorSettings,
    clear_cache,
)
from src.services.anti_ai import (
    AICategory,
    AntiAIDetectionResult,
    RuleBasedAntiAIDetector,
)
from src.services.anti_ai.detectors import RULE_DETECTORS


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_cache()
    yield
    clear_cache()


class TestOrchestrator:
    def test_empty_text(self):
        orch = RuleBasedAntiAIDetector()
        r = orch.detect("")
        assert r.total_score == 100.0
        assert r.violations == []
        for c in AICategory:
            assert r.category_scores[c] == 100.0

    def test_whitespace_only(self):
        orch = RuleBasedAntiAIDetector()
        r = orch.detect("   \n\t  ")
        assert r.total_score == 100.0

    def test_clean_prose(self):
        orch = RuleBasedAntiAIDetector()
        text = "静かな朝だった。鳥がさえずっていた。風も穏やかだった。"
        r = orch.detect(text)
        assert r.total_score == 100.0
        assert r.violations == []

    def test_each_sample_triggers_expected_categories(self):
        from tests.fixtures.anti_ai_samples import (
            TRANSITION_HEAVY,
            SAME_STRUCTURE_TEXT,
            DIRECT_EMOTION_TEXT,
            HEDGING_TEXT,
            TEMPLATE_TEXT,
            UNIFORM_PARAGRAPH_TEXT,
            GENERIC_TEXT,
            CLEAN_PROSE,
        )

        samples_with_expected = [
            (TRANSITION_HEAVY, {AICategory.TRANSITION_OVERUSE}),
            (SAME_STRUCTURE_TEXT, {AICategory.SAME_STRUCTURE}),
            (DIRECT_EMOTION_TEXT, {AICategory.DIRECT_EMOTION}),
            (HEDGING_TEXT, {AICategory.HEDGING_PATTERNS}),
            (TEMPLATE_TEXT, {AICategory.TEMPLATE_PHRASES}),
            (UNIFORM_PARAGRAPH_TEXT, {AICategory.UNIFORM_PARAGRAPH}),
            (GENERIC_TEXT, {AICategory.GENERIC_VOCABULARY}),
        ]
        orch = RuleBasedAntiAIDetector()
        for sample, expected_cats in samples_with_expected:
            r = orch.detect(sample.text)
            triggered = {v.category for v in r.violations}
            missing = expected_cats - triggered
            assert not missing, (
                f"{sample.label}: missing categories {missing}, "
                f"got {sorted(c.value for c in triggered)}"
            )

    def test_clean_prose_does_not_trigger(self):
        from tests.fixtures.anti_ai_samples import CLEAN_PROSE

        orch = RuleBasedAntiAIDetector()
        r = orch.detect(CLEAN_PROSE.text)
        assert r.violations == []
        assert r.total_score == 100.0

    def test_disable_specific_detector(self):
        # All detectors disabled → score 100
        from src.config.anti_ai_config import (
            DetectorSettings,
            DirectEmotionSettings,
            GenericVocabularySettings,
            HedgingSettings,
            SameStructureSettings,
            TemplatePhrasesSettings,
            TransitionOveruseSettings,
            UniformParagraphSettings,
        )

        cfg = AntiAIConfig(
            detectors=DetectorSettings(
                TRANSITION_OVERUSE=TransitionOveruseSettings(enabled=False),
                SAME_STRUCTURE=SameStructureSettings(enabled=False),
                DIRECT_EMOTION=DirectEmotionSettings(enabled=False),
                HEDGING_PATTERNS=HedgingSettings(enabled=False),
                TEMPLATE_PHRASES=TemplatePhrasesSettings(enabled=False),
                UNIFORM_PARAGRAPH=UniformParagraphSettings(enabled=False),
                GENERIC_VOCABULARY=GenericVocabularySettings(enabled=False),
            )
        )
        orch = RuleBasedAntiAIDetector(config=cfg)
        text = "しかし、おそらく、素晴らしい朝だ。重要なことに、結論として。"
        r = orch.detect(text)
        # Everything disabled → 100
        assert r.total_score == 100.0
        assert r.violations == []

    def test_method_label(self):
        orch = RuleBasedAntiAIDetector()
        r = orch.detect("何か")
        assert r.method == "rule_based"

    def test_all_categories_have_scores(self):
        orch = RuleBasedAntiAIDetector()
        r = orch.detect("しかし、走る。さらに、歩く。")
        for c in AICategory:
            assert c in r.category_scores

    def test_to_dict_json_safe(self):
        import json
        orch = RuleBasedAntiAIDetector()
        r = orch.detect("しかし、走る。さらに、歩く。また、跳ねる。")
        d = r.to_dict()
        # Must be JSON-serialisable
        json.dumps(d, ensure_ascii=False)


class TestAsyncWrapper:
    def test_async_matches_sync(self):
        orch = RuleBasedAntiAIDetector()
        text = "しかし、おそらく、素晴らしい朝だ。"
        r_sync = orch.detect(text)
        r_async = asyncio.run(orch.adetect(text))
        assert abs(r_sync.total_score - r_async.total_score) < 1e-6
        assert len(r_sync.violations) == len(r_async.violations)
