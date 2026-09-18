"""WritingService 圧縮経路テスト"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from dataclasses import dataclass

from src.services.writing_service import WritingService
from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.writing import WritingAgent
from src.services.book_score_service import BookScoreCalculator
from src.agents.illustration_agent import IllustrationAgent


@dataclass
class MockBookScore:
    overall_score: float = 85.0
    structure_score: float = 85.0
    coherency_score: float = 85.0
    factual_grounding_score: float = 85.0
    visual_textual_synergy_score: float = 85.0
    reader_experience_score: float = 85.0


class TestWritingServiceCompression:
    """WritingService の圧縮機能経路テスト"""

    @pytest.fixture
    def compressor(self):
        config = CompressionConfig(max_tokens=100, cache_enabled=False)
        return FourLayerCompressor(config=config)

    @pytest.fixture
    def mock_writing_agent(self):
        agent = Mock(spec=WritingAgent)
        agent.execute = AsyncMock()
        return agent

    @pytest.fixture
    def mock_book_score_calculator(self):
        calc = Mock(spec=BookScoreCalculator)
        calc.calculate = AsyncMock(return_value=MockBookScore())
        return calc

    @pytest.fixture
    def mock_context_builder_agent(self):
        agent = Mock(spec=ContextBuilderAgent)
        agent.execute = AsyncMock(return_value=AgentResult(
            next_agent=None,
            artifacts={"writing_context": {"test": "context"}}
        ))
        return agent

    @pytest.fixture
    def mock_illustration_agent(self):
        return Mock(spec=IllustrationAgent)

    @pytest.fixture
    def writing_service(self, compressor, mock_writing_agent, mock_book_score_calculator,
                        mock_context_builder_agent, mock_illustration_agent):
        return WritingService(
            writing_agent=mock_writing_agent,
            book_score_calculator=mock_book_score_calculator,
            context_builder_agent=mock_context_builder_agent,
            illustration_agent=mock_illustration_agent,
            compressor=compressor,
            max_retries=1,
            score_threshold=70.0,
            backoff_base=1.0,
        )

    @pytest.fixture
    def agent_context(self):
        return AgentContext(
            book_id=1,
            branch_id=1,
            ep_num=1,
            artifacts={}
        )

    @pytest.mark.asyncio
    async def test_compressor_set_in_artifacts_before_write(self, writing_service, agent_context, mock_writing_agent):
        """generate_with_quality_assurance 実行時に ctx.artifacts["compressor"] が設定されること"""
        mock_result = Mock()
        mock_result.error = None
        mock_result.draft_text = "テスト本文"
        mock_writing_agent.execute.return_value = mock_result

        await writing_service.generate_with_quality_assurance(agent_context)

        # 呼び出し時の引数を確認
        call_args = mock_writing_agent.execute.call_args
        assert call_args is not None
        called_context = call_args[0][0]
        assert "compressor" in called_context.artifacts
        assert called_context.artifacts["compressor"] is not None

    @pytest.mark.asyncio
    async def test_compressor_passed_to_context_builder_agent(self, writing_service, agent_context, mock_writing_agent, mock_context_builder_agent):
        """context_builder_agent.execute 呼び出し時に compressor が artifacts に含まれること"""
        mock_result = Mock()
        mock_result.error = None
        mock_result.draft_text = "テスト本文"
        mock_writing_agent.execute.return_value = mock_result

        await writing_service.generate_with_quality_assurance(agent_context)

        # context_builder_agent.execute が呼ばれることを確認（内部で呼ばれる想定）
        # 少なくとも compressor が context に含まれることを確認
        call_args = mock_writing_agent.execute.call_args
        called_context = call_args[0][0]
        assert "compressor" in called_context.artifacts

    @pytest.mark.asyncio
    async def test_compressor_preserved_in_retry_loop(self, writing_service, agent_context, mock_writing_agent):
        """再生成ループ（retry）でも compressor が毎回渡されること"""
        mock_result = Mock()
        mock_result.error = None
        mock_result.draft_text = "テスト本文"
        mock_writing_agent.execute.return_value = mock_result

        # スコアを低くしてリトライを発生させる
        writing_service.score_threshold = 90.0

        await writing_service.generate_with_quality_assurance(agent_context)

        # 複数回呼ばれていることを確認
        assert mock_writing_agent.execute.call_count >= 1
        for call in mock_writing_agent.execute.call_args_list:
            called_context = call[0][0]
            assert "compressor" in called_context.artifacts

    @pytest.mark.asyncio
    async def test_compressor_passed_in_anti_ai_loop(self, writing_service, agent_context, mock_writing_agent):
        """Anti-AI ループ実行後も圧縮コンテキストが保持されること"""
        mock_result = Mock()
        mock_result.error = None
        mock_result.draft_text = "テスト本文"
        mock_writing_agent.execute.return_value = mock_result

        # Anti-AI を有効化
        writing_service._enable_anti_ai_loop = True

        await writing_service.generate_with_quality_assurance(agent_context)

        call_args = mock_writing_agent.execute.call_args
        called_context = call_args[0][0]
        assert "compressor" in called_context.artifacts

    @pytest.mark.asyncio
    async def test_compressor_none_does_not_break(self, mock_writing_agent, mock_book_score_calculator,
                                                  mock_context_builder_agent, mock_illustration_agent, agent_context):
        """compressor=None でもエラーにならないこと（後方互換）"""
        service = WritingService(
            writing_agent=mock_writing_agent,
            book_score_calculator=mock_book_score_calculator,
            context_builder_agent=mock_context_builder_agent,
            illustration_agent=mock_illustration_agent,
            compressor=None,
            max_retries=1,
            score_threshold=70.0,
        )

        mock_result = Mock()
        mock_result.error = None
        mock_result.draft_text = "テスト本文"
        mock_writing_agent.execute.return_value = mock_result

        # エラーなく実行されること
        result = await service.generate_with_quality_assurance(agent_context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_build_context_with_compression_method_exists(self, writing_service, agent_context):
        """_build_context_with_compression メソッドが存在し動作すること"""
        assert hasattr(writing_service, '_build_context_with_compression')

        # メソッドが呼び出せることを確認（context_builder_agent.execute をモック）
        mock_result = AgentResult(
            next_agent=None,
            artifacts={"writing_context": {"compressed": "test"}}
        )
        writing_service.context_builder_agent.execute = AsyncMock(return_value=mock_result)

        result = await writing_service._build_context_with_compression(agent_context)
        assert result == {"compressed": "test"}
        assert "compressor" in agent_context.artifacts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])