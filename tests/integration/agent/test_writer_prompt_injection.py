"""Tests for writer prompt emotional context injection."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import RedisVectorStore


class TestWriterPromptInjection:
    """執筆プロンプト感情注入テスト"""

    @pytest.fixture
    def mock_vector_store(self):
        import fakeredis
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        return store

    @pytest.fixture
    def sample_vector(self):
        vec = EmotionalVector(episode_id="ep14")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.3, 0.8, "...", "ep14"))
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 0.9, "...", "ep14", "ep14_betrayal"))
        return vec

    @pytest.mark.asyncio
    async def test_emotional_context_in_prompt(self, mock_vector_store, sample_vector):
        """プロンプトに感情コンテキストが含まれること"""
        # ベクトル保存
        mock_vector_store.upsert("pipeline", "ep14", sample_vector)
        
        # PromptManagerのモック
        from prompts.manager import PromptManager
        
        # 実際のPromptManagerをインスタンス化（依存関係をモック）
        with patch("prompts.manager.RedisVectorStore", return_value=mock_vector_store):
            with patch("prompts.manager.load_character_dict", return_value={"A", "B"}):
                with patch("prompts.manager.build_emotional_context_prompt") as mock_build:
                    mock_build.return_value = "[直前話からの引き継ぎ感情]\nA→B: 恐怖(0.8) [原因: ep14裏切り]"
                    
                    pm = PromptManager()
                    pm.registry = AsyncMock()
                    pm.registry.render_async = AsyncMock(return_value="RENDERED_PROMPT")
                    
                    result = await pm.build_final_writing_prompt(
                        ep_num=15,
                        plot_data={},
                        script_text="テスト脚本",
                        target_word_count=2000,
                        book_id=1,
                    )
                    
                    # 感情コンテキスト生成関数が呼ばれたことを確認
                    mock_build.assert_called_once()
                    
                    # レンダリング時にemotional_contextが渡されたことを確認
                    call_args = pm.registry.render_async.call_args
                    assert call_args is not None
                    context = call_args[0][1]  # 第2引数がcontext
                    assert "emotional_context" in context
                    assert "恐怖(0.8)" in context["emotional_context"]

    @pytest.mark.asyncio
    async def test_no_emotional_context_when_unavailable(self):
        """感情残基モジュールが利用不可の場合"""
        from prompts.manager import PromptManager, EMOTIONAL_RESIDUE_AVAILABLE
        
        # 一時的に利用不可に設定
        original = EMOTIONAL_RESIDUE_AVAILABLE
        import prompts.manager
        prompts.manager.EMOTIONAL_RESIDUE_AVAILABLE = False
        
        try:
            pm = PromptManager()
            pm.registry = AsyncMock()
            pm.registry.render_async = AsyncMock(return_value="RENDERED_PROMPT")
            
            result = await pm.build_final_writing_prompt(
                ep_num=15,
                plot_data={},
                script_text="テスト",
                target_word_count=2000,
                book_id=1,
            )
            
            # emotional_contextが空文字で渡されること
            call_args = pm.registry.render_async.call_args
            context = call_args[0][1]
            assert context["emotional_context"] == ""
        finally:
            prompts.manager.EMOTIONAL_RESIDUE_AVAILABLE = original