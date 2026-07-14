"""tests/test_token_tracker.py - TokenTracker のテスト"""
import pytest
import time

from src.services.token_tracker import TokenTracker
from src.models.report import TokenUsageReport


class TestTokenTracker:
    """TokenTracker のテスト"""

    def test_init(self):
        """初期化テスト"""
        tracker = TokenTracker()
        assert tracker.total_tokens == 0
        assert tracker.input_tokens == 0
        assert tracker.output_tokens == 0
        assert tracker.episode_count == 0
        assert tracker.episode_usages == []

    def test_add_usage(self):
        """使用量加算テスト"""
        tracker = TokenTracker()
        tracker.add_usage(100, 200)
        assert tracker.input_tokens == 100
        assert tracker.output_tokens == 200
        assert tracker.total_tokens == 300

    def test_add_usage_with_ep_num(self):
        """エピソード番号付き使用量加算テスト"""
        tracker = TokenTracker()
        tracker.add_usage(100, 200, ep_num=1)
        tracker.add_usage(150, 250, ep_num=2)
        
        usages = tracker.get_episode_usages()
        assert len(usages) == 2
        assert usages[0]["ep_num"] == 1
        assert usages[0]["total_tokens"] == 300
        assert usages[1]["ep_num"] == 2
        assert usages[1]["total_tokens"] == 400

    def test_increment_episode_count(self):
        """エピソード数インクリメントテスト"""
        tracker = TokenTracker()
        tracker.increment_episode_count()
        tracker.increment_episode_count()
        assert tracker.episode_count == 2

    def test_start_stop(self):
        """開始/停止テスト"""
        tracker = TokenTracker()
        tracker.start()
        time.sleep(0.1)
        tracker.stop()
        
        report = tracker.get_report()
        assert report.generation_time_seconds >= 0.1

    def test_get_report(self):
        """レポート取得テスト"""
        tracker = TokenTracker()
        tracker.add_usage(1000, 2000)
        tracker.increment_episode_count()
        tracker.start()
        time.sleep(0.05)
        tracker.stop()
        
        report = tracker.get_report()
        assert isinstance(report, TokenUsageReport)
        assert report.total_tokens == 3000
        assert report.input_tokens == 1000
        assert report.output_tokens == 2000
        assert report.episode_count == 1
        assert report.generation_time_seconds > 0

    def test_reset(self):
        """リセットテスト"""
        tracker = TokenTracker()
        tracker.add_usage(100, 200)
        tracker.increment_episode_count()
        tracker.reset()
        
        assert tracker.total_tokens == 0
        assert tracker.episode_count == 0