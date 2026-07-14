"""tests/test_episode_writer.py - EpisodeWriter のテスト"""
import pytest

from src.services.episode_writer import EpisodeWriter


class TestEpisodeWriter:
    """EpisodeWriter のテスト"""

    @pytest.fixture
    def writer(self):
        """EpisodeWriterインスタンス"""
        return EpisodeWriter()

    @pytest.mark.asyncio
    async def test_write_first_episode(self, writer):
        """第1話執筆テスト"""
        context = {
            "ep_num": 1,
            "is_first": True,
            "is_last": False,
            "target_word_count": 3000
        }
        
        result = await writer.write(book_id=1, ep_num=1, context=context)
        
        assert "text" in result
        assert "quality_score" in result
        assert "token_usage" in result
        assert len(result["text"]) > 0

    @pytest.mark.asyncio
    async def test_write_with_previous_context(self, writer):
        """前話情報ありでの執筆テスト"""
        context = {
            "ep_num": 2,
            "is_first": False,
            "is_last": False,
            "target_word_count": 3000,
            "previous_episode": {
                "title": "第1話",
                "ending": "戦士は静かに目を閉じた。",
                "summary": "物語的开始"
            }
        }
        
        result = await writer.write(book_id=1, ep_num=2, context=context)
        
        assert "text" in result
        assert len(result["text"]) > 0

    @pytest.mark.asyncio
    async def test_write_fallback_mode(self, writer):
        """フォールバックモードテスト"""
        context = {
            "ep_num": 5,
            "is_first": False,
            "is_last": True,
            "target_word_count": 3000
        }
        
        result = await writer.write(book_id=999, ep_num=5, context=context)
        
        assert "text" in result
        assert "quality_score" in result
        assert "了" in result.text or len(result["text"]) > 0

    def test_word_count_estimate(self, writer):
        """文字数見積テスト"""
        context = {
            "target_word_count": 3000,
            "is_first": False,
            "is_last": False
        }
        
        estimate = writer.word_count_estimate(context)
        assert estimate == 3000

    def test_word_count_estimate_first(self, writer):
        """文字数見積テスト（第1話）"""
        context = {
            "target_word_count": 3000,
            "is_first": True,
            "is_last": False
        }
        
        estimate = writer.word_count_estimate(context)
        assert estimate < 3000  # 開始話は短め

    def test_word_count_estimate_last(self, writer):
        """文字数見積テスト（最終話）"""
        context = {
            "target_word_count": 3000,
            "is_first": False,
            "is_last": True
        }
        
        estimate = writer.word_count_estimate(context)
        assert estimate < 3000  # 最終話も短め