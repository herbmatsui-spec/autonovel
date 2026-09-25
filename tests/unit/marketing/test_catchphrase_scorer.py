"""Step 3: キャッチコピーCTRスコアラーの単体テスト。

35文字超過ペナルティ、最適文字数加点、パワーワード加点、
記号フック加点を検証する。
"""

import pytest

from src.config.kakuyomu_syntax_patterns import (
    CATCHPHRASE_MAX_LENGTH,
    CATCHPHRASE_OPTIMAL_MAX,
    CATCHPHRASE_OPTIMAL_MIN,
)
from src.services.marketing.catchphrase_scorer import score_catchphrase_ctr


class TestCatchphraseScorerLimits:
    """文字数制限に関するテスト。"""

    def test_over_max_length_returns_zero(self) -> None:
        """36字以上は0点判定（カクヨム規定35文字厳守）。"""
        over_length = "あ" * (CATCHPHRASE_MAX_LENGTH + 1)
        assert score_catchphrase_ctr(over_length) == 0

    def test_exactly_max_length_is_scored(self) -> None:
        """ちょうど35文字は0点ではなく評価対象。"""
        exactly_max = "あ" * CATCHPHRASE_MAX_LENGTH
        assert score_catchphrase_ctr(exactly_max) > 0

    def test_empty_string_scores_low(self) -> None:
        """空文字は低スコア（基礎点+文字数減点の下限で20点）。"""
        assert score_catchphrase_ctr("") <= 20
        assert score_catchphrase_ctr("") < score_catchphrase_ctr("あ" * 20)

    def test_score_within_0_to_100(self) -> None:
        """スコアは必ず0〜100の範囲内。"""
        for text in ("", "短い", "あ" * 20, "「全滅」――実は！", "あ" * 100):
            score = score_catchphrase_ctr(text)
            assert 0 <= score <= 100


class TestCatchphraseScorerOptimalLength:
    """スマホ視認性（最適文字数）のテスト。"""

    def test_optimal_range_scores_higher_than_short(self) -> None:
        """15〜32字は15字未満より高スコア。"""
        optimal = "あ" * 20
        short = "あ" * 5
        assert score_catchphrase_ctr(optimal) > score_catchphrase_ctr(short)

    def test_min_optimal_boundary(self) -> None:
        """15字ちょうどは最適範囲。"""
        boundary = "あ" * CATCHPHRASE_OPTIMAL_MIN
        below = "あ" * (CATCHPHRASE_OPTIMAL_MIN - 1)
        assert score_catchphrase_ctr(boundary) > score_catchphrase_ctr(below)

    def test_max_optimal_boundary(self) -> None:
        """32字ちょうどは最適範囲。"""
        boundary = "あ" * CATCHPHRASE_OPTIMAL_MAX
        over = "あ" * (CATCHPHRASE_OPTIMAL_MAX + 1)
        assert score_catchphrase_ctr(boundary) >= score_catchphrase_ctr(over)


class TestCatchphraseScorerPowerWords:
    """パワーワード含有判定のテスト。"""

    def test_power_word_increases_score(self) -> None:
        """パワーワード含有で加点される。"""
        base = "あ" * 20
        with_power = "全滅したあ" * 3
        with_power = (with_power + "あ" * 20)[:20]
        assert score_catchphrase_ctr(with_power) > score_catchphrase_ctr(base)

    def test_multiple_power_words_increase_score(self) -> None:
        """複数パワーワードで単一より高スコア。"""
        one = ("実は" + "あ" * 20)[:20]
        two = ("実は" + "全滅" + "あ" * 20)[:20]
        assert score_catchphrase_ctr(two) > score_catchphrase_ctr(one)


class TestCatchphraseScorerHooks:
    """記号フック判定のテスト。"""

    def test_quotation_brackets_increase_score(self) -> None:
        """カギ括弧「」で加点される。"""
        base = "あ" * 20
        hooked = "「あ」" + "あ" * 17
        assert score_catchphrase_ctr(hooked) > score_catchphrase_ctr(base)

    def test_dash_and_marks_increase_score(self) -> None:
        """――や！？で加点される。"""
        base = "あ" * 20
        hooked = "あ！？――" + "あ" * 16
        assert score_catchphrase_ctr(hooked) > score_catchphrase_ctr(base)

    def test_realistic_high_ctr_catchphrase_scores_high(self) -> None:
        """実戦的な高CTRコピーは高スコア。"""
        high_ctr = "「お前はクビだ」――そう言った元パーティが翌日全滅していた件。"
        assert score_catchphrase_ctr(high_ctr) >= 80
