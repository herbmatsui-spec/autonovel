#!/usr/bin/env python3
"""
書記エージェント・コンポーネントの単体テスト

EpisodeWriter, RewriteOrchestrator, BibleExtractor, ContextBuilder のテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, Optional

from src.agents.writing.episode_writer import EpisodeWriter
from src.agents.writing.rewrite_orchestrator import RewriteOrchestrator
from src.agents.writing.bible_extractor import BibleExtractor
from src.agents.context_builder import ContextBuilder
from src.services.llm_service import LLMService
from src.shared.result import Result


class TestEpisodeWriter:
    """EpisodeWriter のテスト"""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock(spec=LLMService)
        # GenerateResult オブジェクトを模倣
        mock_result = MagicMock()
        mock_result.story_content = "生成された本文です。" * 10
        llm.generate_text = AsyncMock(return_value=mock_result)
        return llm

    @pytest.fixture
    def mock_context_builder(self):
        builder = MagicMock(spec=ContextBuilder)
        builder.build_full_writing_context = AsyncMock(return_value={
            "plot": {"summary": "テストプロット", "detailed_blueprint": "詳細プロット"},
            "characters": [{"name": "主人公", "role": "主役"}],
            "world_building": "テスト世界観",
            "char_static_ctx": "静的キャラ情報",
            "char_dynamic_ctx": "動的キャラ情報",
            "prev_ctx": "前話情報",
            "pov_character_name": "主人公",
            "script": "",
        })
        return builder

    @pytest.fixture
    def mock_prompt_manager(self):
        pm = MagicMock()
        pm.build_final_writing_prompt = AsyncMock(return_value="完成されたプロンプト")
        return pm

    @pytest.fixture
    def episode_writer(self, mock_llm, mock_context_builder, mock_prompt_manager):
        writer = EpisodeWriter(
            llm=mock_llm,
            context_builder=mock_context_builder,
            prompt_manager=mock_prompt_manager,
        )
        # 内部で使われる属性を設定（PromptComposer, EroticEnhancer 用）
        writer.prompt_manager = mock_prompt_manager
        writer.logger = MagicMock()
        return writer

    @pytest.mark.asyncio
    async def test_write_normal_mode(self, episode_writer, mock_llm, mock_prompt_manager):
        """通常モードでの本文生成テスト"""
        context = {
            "plot": {"summary": "テストプロット", "detailed_blueprint": "詳細"},
            "characters": [],
            "world_building": "",
            "char_static_ctx": "",
            "char_dynamic_ctx": "",
            "prev_ctx": "",
            "pov_character_name": "主人公",
            "erotic_intensity": 0,
        }
        
        result = await episode_writer.write(1, 1, context)
        
        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.generate_text.assert_called_once()
        call_args = mock_llm.generate_text.call_args
        assert call_args.kwargs["purpose"] == "writing"
        assert call_args.kwargs["nsfw_mode"] is False
        mock_prompt_manager.build_final_writing_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_erotic_mode(self, episode_writer, mock_llm, mock_prompt_manager):
        """官能モードでの本文生成テスト"""
        context = {
            "plot": {"summary": "テストプロット", "detailed_blueprint": "詳細"},
            "characters": [],
            "world_building": "",
            "char_static_ctx": "",
            "char_dynamic_ctx": "",
            "prev_ctx": "",
            "pov_character_name": "主人公",
            "erotic_intensity": 5,
            "nsfw_enabled": True,
        }
        
        result = await episode_writer.write(1, 1, context)
        
        assert isinstance(result, str)
        call_args = mock_llm.generate_text.call_args
        assert call_args.kwargs["nsfw_mode"] is True

    @pytest.mark.asyncio
    async def test_write_llm_exception_handling(self, episode_writer, mock_llm):
        """LLM呼び出し例外時の処理テスト"""
        mock_llm.generate_text = AsyncMock(side_effect=RuntimeError("LLM error"))
        
        context = {
            "plot": {"summary": "テスト", "detailed_blueprint": "詳細"},
            "characters": [],
            "world_building": "",
            "char_static_ctx": "",
            "char_dynamic_ctx": "",
            "prev_ctx": "",
            "pov_character_name": "主人公",
            "erotic_intensity": 0,
        }
        
        # 例外が伝播することを確認
        with pytest.raises(RuntimeError, match="LLM error"):
            await episode_writer.write(1, 1, context)


class TestRewriteOrchestrator:
    """RewriteOrchestrator のテスト"""

    @pytest.fixture
    def mock_writer(self):
        writer = MagicMock()
        writer.rewrite = AsyncMock(return_value="リライト後の本文")
        return writer

    @pytest.fixture
    def mock_auditor(self):
        auditor = MagicMock()
        auditor.audit = AsyncMock(return_value={"score": 80, "improvements": ["改善点1"]})
        return auditor

    @pytest.fixture
    def mock_spice_guard(self):
        guard = MagicMock()
        guard.extract_spice = MagicMock(return_value="抽出されたスパイス")
        return guard

    @pytest.fixture
    def orchestrator(self, mock_writer, mock_auditor, mock_spice_guard):
        return RewriteOrchestrator(
            writer=mock_writer,
            auditor=mock_auditor,
            spice_guard=mock_spice_guard,
        )

    @pytest.mark.asyncio
    async def test_rewrite_until_pass_no_auditor(self, mock_writer):
        """auditor未設定時はリライトをスキップ"""
        orchestrator = RewriteOrchestrator(writer=mock_writer, auditor=None)
        
        result = await orchestrator.rewrite_until_pass("元の本文", {})
        
        assert result.is_ok  # プロパティ
        assert result.value["iterations"] == 0
        assert result.value["content"] == "元の本文"
        mock_writer.rewrite.assert_not_called()

    @pytest.mark.asyncio
    async def test_rewrite_until_pass_early_exit(self, orchestrator):
        """初回監査で目標スコア達成時は即座に返却"""
        orchestrator.auditor.audit = AsyncMock(return_value={"score": 98, "improvements": []})
        
        result = await orchestrator.rewrite_until_pass("元の本文", {}, target_score=95.0)
        
        assert result.is_ok
        assert result.value["iterations"] == 0
        assert result.value["content"] == "元の本文"
        orchestrator.writer.rewrite.assert_not_called()

    @pytest.mark.asyncio
    async def test_rewrite_until_pass_multiple_iterations(self, orchestrator):
        """複数回リライトが実行されることを確認"""
        # 1回目: 80点, 2回目: 97点
        orchestrator.auditor.audit = AsyncMock(
            side_effect=[
                {"score": 80, "improvements": ["改善1"]},
                {"score": 97, "improvements": []},
            ]
        )
        
        result = await orchestrator.rewrite_until_pass("元の本文", {}, max_iter=3, target_score=95.0)
        
        assert result.is_ok
        # 0-indexed: i=0で失敗→リライト、i=1で成功 → iterations=1
        assert result.value["iterations"] == 1
        assert orchestrator.writer.rewrite.call_count == 1

    @pytest.mark.asyncio
    async def test_rewrite_until_pass_max_iterations(self, orchestrator):
        """最大回数までリライトしても目標未達の場合"""
        orchestrator.auditor.audit = AsyncMock(return_value={"score": 80, "improvements": ["改善"]})
        
        result = await orchestrator.rewrite_until_pass("元の本文", {}, max_iter=2, target_score=95.0)
        
        assert result.is_ok
        assert result.value["iterations"] == 2
        assert result.value["needs_human_review"] is True
        assert orchestrator.writer.rewrite.call_count == 2

    @pytest.mark.asyncio
    async def test_rewrite_with_spice_guard(self, orchestrator, mock_spice_guard):
        """SpiceGuard が呼ばれることを確認"""
        orchestrator.auditor.audit = AsyncMock(
            side_effect=[
                {"score": 80, "improvements": ["改善"]},
                {"score": 97, "improvements": []},
            ]
        )
        
        await orchestrator.rewrite_until_pass("元の本文", {}, max_iter=2, target_score=95.0)
        
        mock_spice_guard.extract_spice.assert_called_once_with("元の本文")


class TestBibleExtractor:
    """BibleExtractor のテスト"""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock(spec=LLMService)
        llm.generate_json = AsyncMock(return_value={
            "characters": [{"name": "主人公", "role": "主役"}],
            "world_building": "抽出された世界観",
        })
        return llm

    @pytest.fixture
    def extractor(self, mock_llm):
        return BibleExtractor(llm=mock_llm)

    @pytest.mark.asyncio
    async def test_extract_stub_returns_none(self, extractor):
        """現在のスタブ実装では None が返る"""
        result = await extractor.extract(1, "本文", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_with_mock_llm(self, extractor, mock_llm):
        """モックLLMで将来的な実装をシミュレート"""
        # 将来的に generate_json を呼ぶ実装になった場合のテスト
        mock_llm.generate_json = AsyncMock(return_value={
            "characters": [{"name": "テストキャラ"}],
            "world_building": "テスト世界",
        })
        
        # 現在の実装は generate_json を呼ばないが、インターフェースの確認
        result = await extractor.extract(1, "本文", None)
        assert result is None


class TestContextBuilder:
    """ContextBuilder の境界値テスト"""

    @pytest.fixture
    def mock_repo(self):
        repo = MagicMock()
        repo.get_plot = AsyncMock(return_value=None)
        repo.get_book = AsyncMock(return_value=None)
        repo.get_all_characters = AsyncMock(return_value=[])
        repo.get_chapter = AsyncMock(return_value=None)
        repo.get_latest_bible = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_agent(self, mock_repo):
        from src.agents.base import BaseAgent
        agent = MagicMock(spec=BaseAgent)
        agent.repo = mock_repo
        agent._plot_expander = None
        agent.logger = MagicMock()
        return agent

    @pytest.fixture
    def context_builder(self, mock_agent):
        return ContextBuilder(mock_agent)

    @pytest.mark.asyncio
    async def test_build_context_no_plot(self, context_builder):
        """プロットなしの場合"""
        context = await context_builder.build_full_writing_context(1, 1, 1, 2000)
        
        assert "plot" in context
        # 空のプロットオブジェクトが返される（Noneや{}ではない）
        assert isinstance(context["plot"], dict)

    @pytest.mark.asyncio
    async def test_build_context_no_characters(self, context_builder):
        """キャラクターなしの場合"""
        context = await context_builder.build_full_writing_context(1, 1, 1, 2000)
        
        # characters キーが存在するか、関連するキーが存在する
        assert "char_static_ctx" in context or "characters" in context

    @pytest.mark.asyncio
    async def test_build_context_no_previous_chapter(self, context_builder):
        """前話なしの場合（ep_num=1）"""
        context = await context_builder.build_full_writing_context(1, 1, 1, 2000)
        
        assert "prev_chapter" in context or "prev_ctx" in context

    @pytest.mark.asyncio
    async def test_build_context_empty_world_state(self, context_builder):
        """ワールドステートなしの場合"""
        context = await context_builder.build_full_writing_context(1, 1, 1, 2000)
        
        # world_building または関連するキーが存在
        assert any(k in context for k in ["world_state", "world_building", "density_level"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])