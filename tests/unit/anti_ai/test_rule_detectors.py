"""Unit tests for the seven rule-based detectors."""

from __future__ import annotations

import pytest

from src.config.anti_ai_config import (
    AntiAIConfig,
    DetectorSettings,
    DirectEmotionSettings,
    GenericVocabularySettings,
    HedgingSettings,
    SameStructureSettings,
    TemplatePhrasesSettings,
    TransitionOveruseSettings,
    UniformParagraphSettings,
    clear_cache,
)
from src.services.anti_ai.detectors import (
    DirectEmotionDetector,
    GenericVocabularyDetector,
    HedgingPatternsDetector,
    SameStructureDetector,
    TemplatePhrasesDetector,
    TransitionOveruseDetector,
    UniformParagraphDetector,
)
from src.services.anti_ai.models import AICategory, Severity


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_cache()
    yield
    clear_cache()


def _check_sorted(violations):
    for i in range(len(violations) - 1):
        assert violations[i].start <= violations[i + 1].start


def _check_offsets(text, violations):
    for v in violations:
        actual = text[v.start : v.end]
        assert actual == v.matched_text, f"offset mismatch: {actual!r} vs {v.matched_text!r}"


class TestTransitionOveruseDetector:
    def setup_method(self):
        self.d = TransitionOveruseDetector()

    def test_no_transitions(self):
        text = "静かな朝だった。鳥が鳴いていた。風も穏やかだった。"
        v = self.d.detect(text)
        # Below threshold so detector filters out
        assert len(v) == 0

    def test_many_transitions(self):
        text = "しかし、走った。さらに、飛んだ。また、笑った。なお、泣いた。"
        v = self.d.detect(text)
        assert len(v) >= 3
        _check_sorted(v)
        _check_offsets(text, v)

    def test_disabled_in_config(self):
        cfg = AntiAIConfig(
            detectors=DetectorSettings(
                TRANSITION_OVERUSE=TransitionOveruseSettings(enabled=False)
            )
        )
        d = TransitionOveruseDetector(config=cfg)
        v = d.detect("しかし、走る。さらに、歩く。また、跳ねる。")
        assert len(v) == 0

    def test_score_in_range(self):
        v = self.d.detect("しかし、走る。さらに、歩く。また、跳ねる。なお、泳ぐ。")
        s = self.d.score_from_violations(
            "しかし、走る。さらに、歩く。また、跳ねる。なお、泳ぐ。", v
        )
        assert 0 <= s <= 100


class TestSameStructureDetector:
    def setup_method(self):
        self.d = SameStructureDetector()

    def test_no_consecutive(self):
        text = "走った。笑った。泣いた。怒った。喜んだ。"  # 5 different ends
        v = self.d.detect(text)
        assert len(v) == 0

    def test_three_consecutive_ta(self):
        text = "彼は走った。彼女は走った。世界は走った。"
        v = self.d.detect(text)
        assert len(v) >= 1
        _check_offsets(text, v)

    def test_disabled(self):
        cfg = AntiAIConfig(
            detectors=DetectorSettings(
                SAME_STRUCTURE=SameStructureSettings(enabled=False)
            )
        )
        d = SameStructureDetector(config=cfg)
        assert d.detect("走った。走った。走った。") == []

    def test_custom_count(self):
        cfg = AntiAIConfig(
            detectors=DetectorSettings(
                SAME_STRUCTURE=SameStructureSettings(consecutive_count=4)
            )
        )
        d = SameStructureDetector(config=cfg)
        v = d.detect("走った。走った。走った。")  # only 3
        assert len(v) == 0


class TestDirectEmotionDetector:
    def setup_method(self):
        self.d = DirectEmotionDetector()

    def test_no_emotion(self):
        text = "雨が降る。風が吹く。鳥が鳴く。"
        assert self.d.detect(text) == []

    def test_below_limit(self):
        text = "悲しいと思った。風が頬を叩く。懐かしいと感じた。"
        # 2 direct emotions in one paragraph, at the limit
        v = self.d.detect(text)
        # At exactly the limit, not over it
        assert len(v) == 0

    def test_above_limit(self):
        text = (
            "悲しいと思った。風が頬を叩く。懐かしいと感じた。"
            "つまらないと思った。最後に、怒りを覚えた。"
        )
        v = self.d.detect(text)
        assert len(v) >= 1
        _check_offsets(text, v)


class TestHedgingPatternsDetector:
    def setup_method(self):
        self.d = HedgingPatternsDetector()

    def test_no_hedging(self):
        text = "彼は走った。彼女も走った。一緒に笑った。"
        assert self.d.detect(text) == []

    def test_lots_of_hedging(self):
        text = "おそらく来る、たぶん来る、かもしれません、そうだと思います。"
        v = self.d.detect(text)
        assert len(v) >= 2
        _check_sorted(v)
        _check_offsets(text, v)

    def test_disabled(self):
        cfg = AntiAIConfig(
            detectors=DetectorSettings(HEDGING_PATTERNS=HedgingSettings(enabled=False))
        )
        d = HedgingPatternsDetector(config=cfg)
        assert d.detect("おそらく、たぶん、かもしれません。") == []


class TestTemplatePhrasesDetector:
    def setup_method(self):
        self.d = TemplatePhrasesDetector()

    def test_no_template(self):
        text = "静かな朝だった。鳥がさえずっていた。"
        assert self.d.detect(text) == []

    def test_templates_found(self):
        text = "重要なことに、彼は走った。注目すべきは、その後だ。結論として、成功した。"
        v = self.d.detect(text)
        assert len(v) >= 2
        _check_sorted(v)
        _check_offsets(text, v)

    def test_min_matches_threshold(self):
        cfg = AntiAIConfig(
            detectors=DetectorSettings(
                TEMPLATE_PHRASES=TemplatePhrasesSettings(min_matches=5)
            )
        )
        d = TemplatePhrasesDetector(config=cfg)
        # Only 2 matches, but config requires 5 → no violations
        v = d.detect("重要なことには、注目すべきは、結論として、")
        assert len(v) == 0


class TestUniformParagraphDetector:
    def setup_method(self):
        self.d = UniformParagraphDetector()

    def test_too_few_paragraphs(self):
        text = "短い。\n\nたった一つ。"
        assert self.d.detect(text) == []

    def test_uniform_paragraphs(self):
        text = "森は静かだった。霧が低く垂れていた。風が鳴っていた。\n\n光は弱かった。草が揺れていた。鳥が泣いていた。\n\n道は細かった。水が流れていた。影が伸びていた。"
        v = self.d.detect(text)
        assert len(v) >= 3
        _check_offsets(text, v)

    def test_varied_lengths(self):
        # Each paragraph is very different in length
        text = "短い。\n\n" "これは中くらいの長さの段落で、もう少し長い。\n\n" "非常に長い段落を書いています。物語は続くのでした。長い長い文章は読者を引き込むものなのです。"
        v = self.d.detect(text)
        assert len(v) == 0


class TestGenericVocabularyDetector:
    def setup_method(self):
        self.d = GenericVocabularyDetector()

    def test_no_generic(self):
        text = "雨が降る。風が吹く。鳥が鳴く。"
        assert self.d.detect(text) == []

    def test_generic_terms(self):
        text = "素晴らしい朝だ。興味深い人物だ。多様な意見がある。"
        v = self.d.detect(text)
        assert len(v) >= 3
        _check_offsets(text, v)

    def test_score_in_range(self):
        text = "素晴らしい。興味深い。多様な。重要な。深刻な。様々な。"
        v = self.d.detect(text)
        s = self.d.score_from_violations(text, v)
        assert 0 <= s <= 100
