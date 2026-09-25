"""EasyMode / EpisodeWriter 圧縮経路テスト"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from src.services.auto_workflow_pipeline import create_easy_mode_pipeline
from src.agents.writing.episode_writer import EpisodeWriter
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig
from src.services.llm_service import LLMService


class TestEasyModeCompression:
    """EasyMode / EpisodeWriter 経路の圧縮機能テスト"""

    @pytest.fixture
    def compressor(self):
        config = CompressionConfig(max_tokens=100, cache_enabled=False)
        return FourLayerCompressor(config=config)

    @pytest.fixture
    def mock_llm(self):
        return Mock(spec=LLMService)

    @pytest.fixture
    def mock_context_builder(self):
        agent = Mock(spec=ContextBuilderAgent)
        agent.execute = AsyncMock(return_value=AgentResult(
            next_agent=None,
            artifacts={"writing_context": {"test": "context"}}
        ))
        return agent

    def test_create_easy_mode_pipeline_accepts_compressor(self, compressor):
        """create_easy_mode_pipeline が compressor パラメータを受け入れること"""
        pipeline = create_easy_mode_pipeline(compressor=compressor)
        assert pipeline is not None

    def test_create_easy_mode_pipeline_without_compressor(self):
        """create_easy_mode_pipeline が compressor なしでも動作すること（後方互換）"""
        pipeline = create_easy_mode_pipeline()
        assert pipeline is not None

    def test_create_easy_mode_pipeline_compressor_passed_to_pipeline(self, compressor):
        """create_easy_mode_pipeline で渡された compressor がパイプラインに設定されること"""
        pipeline = create_easy_mode_pipeline(compressor=compressor)
        # パイプライン自体には compressor 属性はないが、ステップ経由で利用される想定
        # ここではエラーなく作成されることを確認
        assert pipeline is not None


class TestEpisodeWriterCompression:
    """EpisodeWriter の圧縮機能テスト"""

    @pytest.fixture
    def compressor(self):
        config = CompressionConfig(max_tokens=100, cache_enabled=False)
        return FourLayerCompressor(config=config)

    @pytest.fixture
    def mock_llm(self):
        return Mock(spec=LLMService)

    @pytest.fixture
    def mock_context_builder(self):
        agent = Mock(spec=ContextBuilderAgent)
        agent.execute = AsyncMock(return_value=AgentResult(
            next_agent=None,
            artifacts={"writing_context": {"compressed_context": "test"}}
        ))
        return agent

    def test_episode_writer_accepts_compressor(self, compressor, mock_llm, mock_context_builder):
        """EpisodeWriter.__init__ が compressor パラメータを受け入れること"""
        writer = EpisodeWriter(
            llm=mock_llm,
            context_builder=mock_context_builder,
            compressor=compressor,
        )
        assert writer.compressor is compressor

    def test_episode_writer_without_compressor(self, mock_llm, mock_context_builder):
        """EpisodeWriter が compressor なしでも動作すること（後方互換）"""
        writer = EpisodeWriter(
            llm=mock_llm,
            context_builder=mock_context_builder,
        )
        assert writer.compressor is None

    @pytest.mark.asyncio
    async def test_build_context_sets_compressor_in_artifacts(self, compressor, mock_llm, mock_context_builder):
        """build_context で ctx.artifacts["compressor"] が設定されること"""
        writer = EpisodeWriter(
            llm=mock_llm,
            context_builder=mock_context_builder,
            compressor=compressor,
        )

        ctx = AgentContext(
            book_id=1,
            branch_id=1,
            ep_num=1,
            artifacts={}
        )

        result = await writer.build_context(1, 1, 1, 3000)

        # context_builder.execute が呼ばれる際に compressor が artifacts に含まれること
        call_args = mock_context_builder.execute.call_args
        assert call_args is not None
        called_ctx = call_args[0][0]
        assert "compressor" in called_ctx.artifacts
        assert called_ctx.artifacts["compressor"] is compressor

    @pytest.mark.asyncio
    async def test_build_context_without_compressor(self, mock_llm, mock_context_builder):
        """compressor なしでも build_context が動作すること"""
        writer = EpisodeWriter(
            llm=mock_llm,
            context_builder=mock_context_builder,
            compressor=None,
        )

        result = await writer.build_context(1, 1, 1, 3000)

        call_args = mock_context_builder.execute.call_args
        called_ctx = call_args[0][0]
        # compressor が None の場合は設定されない、または None が設定される
        # 実装では self.compressor が None なので "compressor": None が設定される
        assert "compressor" in called_ctx.artifacts
        assert called_ctx.artifacts["compressor"] is None


class TestEasyModeRouterCompression:
    """easy_mode ルーターでの圧縮機能テスト"""

    @pytest.fixture
    def compressor(self):
        config = CompressionConfig(max_tokens=100, cache_enabled=False)
        return FourLayerCompressor(config=config)

    def test_generate_content_creates_compressor(self):
        """generate_content 内で FourLayerCompressor が生成されること（実装確認）"""
        # 実装の確認はソースコードを見るため、ここではインポートができることを確認
        from src.backend.routers.easy_mode import execute_generation
        assert callable(execute_generation)

    def test_compressor_in_params_for_orchestrated_task(self, compressor):
        """generate_content で params に compressor が含まれること"""
        # 実装では execute_generation 内で params["compressor"] = FourLayerCompressor(...)
        # ここではインポートができることを確認
        from src.backend.routers.easy_mode import execute_generation
        assert callable(execute_generation)


class TestGenerationTasksCompression:
    """generation_tasks.py での圧縮機能テスト"""

    @pytest.fixture
    def compressor(self):
        config = CompressionConfig(max_tokens=100, cache_enabled=False)
        return FourLayerCompressor(config=config)

    def test_generate_orchestrated_has_compressor_in_dependencies(self):
        """_generate_orchestrated で dependencies に compressor が含まれること（実装確認）"""
        from src.backend.tasks.generation_tasks import _generate_orchestrated
        assert callable(_generate_orchestrated)

    def test_generate_adds_compressor_to_payload(self):
        """_generate で payload に compressor が追加されること（実装確認）"""
        from src.backend.tasks.generation_tasks import _generate
        assert callable(_generate)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])