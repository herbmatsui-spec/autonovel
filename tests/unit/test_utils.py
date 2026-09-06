import pytest

from src.shared.utils import estimate_tokens, TokenUsageTracker


class TestEstimateTokens:
    def test_empty_string_returns_zero(self):
        assert estimate_tokens("") == 0

    def test_none_input_returns_zero(self):
        assert estimate_tokens(None) == 0  # type: ignore[arg-type]

    def test_japanese_text_estimation(self):
        # Japanese characters: ~0.7 tokens per char
        # Note: \w+ also matches Japanese words, so "世界" counts as 1 word
        text = "こんにちは世界"  # 7 chars, 1 word (世界)
        tokens = estimate_tokens(text)
        # 7 * 0.7 + 1 * 1.3 = 4.9 + 1.3 = 6.2 -> 6
        assert tokens == 6

    def test_english_text_estimation(self):
        # English words: ~1.3 tokens per word
        text = "hello world"
        tokens = estimate_tokens(text)
        assert tokens == int(2 * 1.3)

    def test_mixed_text_estimation(self):
        text = "hello 世界"
        # 2 english words + 2 japanese chars
        tokens = estimate_tokens(text)
        expected = int(2 * 1.3 + 2 * 0.7)
        assert tokens == expected

    def test_text_with_symbols_and_numbers(self):
        text = "test123!@# 日本語"
        tokens = estimate_tokens(text)
        # 1 word (test123) + 4 japanese chars
        expected = int(1 * 1.3 + 4 * 0.7)
        assert tokens == expected

    def test_long_text_estimation(self):
        text = "a " * 1000  # 1000 words
        tokens = estimate_tokens(text)
        assert tokens == int(1000 * 1.3)


class TestTokenUsageTracker:
    def test_init_creates_tracker_with_stats_dict(self):
        stats = {"prompt": 0, "completion": 0, "calls": 0}
        tracker = TokenUsageTracker(stats)
        assert tracker.stats is stats

    def test_add_usage_increments_counters(self):
        stats = {"prompt": 100, "completion": 50, "calls": 1}
        tracker = TokenUsageTracker(stats)
        tracker.add_usage(50, 25)
        assert stats["prompt"] == 150
        assert stats["completion"] == 75
        assert stats["calls"] == 2

    def test_add_usage_multiple_calls(self):
        stats = {"prompt": 0, "completion": 0, "calls": 0}
        tracker = TokenUsageTracker(stats)
        tracker.add_usage(100, 50)
        tracker.add_usage(200, 100)
        tracker.add_usage(50, 25)
        assert stats["prompt"] == 350
        assert stats["completion"] == 175
        assert stats["calls"] == 3

    def test_get_cost_usd_calculates_correctly(self):
        stats = {"prompt": 1_000_000, "completion": 500_000, "calls": 10}
        tracker = TokenUsageTracker(stats)
        # input: 1M * 0.00000025 = 0.25
        # output: 500K * 0.0000015 = 0.75
        # total: 1.00
        cost = tracker.get_cost_usd()
        assert cost == 1.0

    def test_get_cost_usd_zero_usage(self):
        stats = {"prompt": 0, "completion": 0, "calls": 0}
        tracker = TokenUsageTracker(stats)
        assert tracker.get_cost_usd() == 0.0

    def test_get_summary_returns_formatted_string(self):
        stats = {"prompt": 1000, "completion": 500, "calls": 5}
        tracker = TokenUsageTracker(stats)
        summary = tracker.get_summary()
        assert "API呼び出し: 5回" in summary
        assert "推定コスト: $" in summary

    def test_get_summary_with_zero_calls(self):
        stats = {"prompt": 0, "completion": 0, "calls": 0}
        tracker = TokenUsageTracker(stats)
        summary = tracker.get_summary()
        assert "API呼び出し: 0回" in summary
        assert "推定コスト: $0.0000" in summary