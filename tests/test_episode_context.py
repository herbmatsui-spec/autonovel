"""tests/test_episode_context.py - EpisodeContextBuilder のテスト"""
import pytest

from src.services.episode_context import EpisodeContextBuilder


class TestEpisodeContextBuilder:
    """EpisodeContextBuilder のテスト"""

    @pytest.fixture
    def builder(self):
        """EpisodeContextBuilderインスタンス"""
        return EpisodeContextBuilder()

    def test_build_context_first_episode(self, builder):
        """第1話のコンテキスト生成テスト"""
        context = builder.build_context(
            book_id=1,
            ep_num=1,
            target_word_count=3000
        )
        
        assert context["book_id"] == 1
        assert context["ep_num"] == 1
        assert context["is_first"] is True
        assert context["is_last"] is False
        assert context["target_word_count"] == 3000

    def test_build_context_with_previous(self, builder):
        """前話情報ありのコンテキスト生成テスト"""
        previous = {
            "title": "第1話",
            "ending": "戦士は静かに目を閉じた。",
            "summary": "物語の始まり"
        }
        
        context = builder.build_context(
            book_id=1,
            ep_num=2,
            target_word_count=3000,
            previous_episode=previous
        )
        
        assert context["is_first"] is False
        assert "previous_episode" in context
        assert context["previous_episode"]["ending"] == "戦士は静かに目を閉じた。"

    def test_history_tracking(self, builder):
        """履歴追跡テスト"""
        builder.build_context(book_id=1, ep_num=1, target_word_count=3000)
        builder.build_context(book_id=1, ep_num=2, target_word_count=3000)
        
        history = builder.get_history()
        assert len(history) == 2
        assert history[0]["ep_num"] == 1
        assert history[1]["ep_num"] == 2

    def test_clear_history(self, builder):
        """履歴クリアテスト"""
        builder.build_context(book_id=1, ep_num=1, target_word_count=3000)
        builder.build_context(book_id=1, ep_num=2, target_word_count=3000)
        
        builder.clear_history()
        
        history = builder.get_history()
        assert len(history) == 0

    def test_set_final_episode(self, builder):
        """最終話フラグ設定テスト"""
        builder.build_context(book_id=1, ep_num=1, target_word_count=3000)
        builder.build_context(book_id=1, ep_num=2, target_word_count=3000)
        
        builder.set_final_episode(2)
        
        history = builder.get_history()
        assert history[1]["context"]["is_last"] is True

    def test_history_limit(self, builder):
        """履歴上限テスト（10話分のみ保持）"""
        for i in range(1, 16):
            builder.build_context(book_id=1, ep_num=i, target_word_count=3000)
        
        history = builder.get_history()
        assert len(history) == 10  # 最新10話のみ
        assert history[0]["ep_num"] == 6  # 6-15話の范围