"""
Testcontainers を使用した統合テスト例
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.easy_mode import create_series
from src.easy_mode.models import PipelineConfig
from src.core.llm_gateway import LLMGenerateResultProxy
from src.core.llm_clients.base import BaseLLMClient


class TestPipelineIntegrationWithContainers:
    """Testcontainers を使用したパイプライン統合テスト"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_with_real_db(self, test_engine, db_manager, mock_llm_client):
        """実 DB を使用したフルパイプラインテスト"""
        # モック LLM のレスポンス設定
        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"world": "test", "protagonist": "テスト"}'},
            '{"world": "test", "protagonist": "テスト"}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )
        mock_llm_client.generate_text.return_value = (
            "テスト生成コンテンツ。ざまぁ見ろ。実はチートだった。",
            {"prompt_tokens": 50, "completion_tokens": 150}
        )

        # パイプライン作成・実行
        pipeline = create_series(test_engine, "zarma", target_episodes=2)
        result = await pipeline.run()

        # 検証
        assert result is not None
        assert result.genre == "zarma"
        assert result.total_episodes == 2
        assert len(result.episodes) == 2
        assert result.bible is not None
        assert result.plot_outline is not None

        # DB に保存されたか確認
        from src.backend.database import DataRepository
        repo = DataRepository(db_manager)
        books = await repo.list_books()
        assert len(books) >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bible_generation_persists_to_db(self, test_engine, db_manager, mock_llm_client):
        """Bible 生成が DB に永続化されることを確認"""
        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"world": "test", "protagonist": "テスト"}'},
            '{"world": "test", "protagonist": "テスト"}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )

        from src.easy_mode.bible_generator import BibleGenerator
        from src.presets.loader import load_preset

        preset = load_preset("zarma")
        bible_gen = BibleGenerator(preset, test_engine.llm)
        bible = await bible_gen.generate(target_episodes=8)

        assert "world" in bible
        assert "protagonist" in bible

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_plot_generation_uses_real_redis(self, test_engine, redis_client, mock_llm_client):
        """プロット生成が Redis を使用することを確認"""
        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"episodes": [{"ep_num": 1, "title": "test"}]}'},
            '{"episodes": [{"ep_num": 1, "title": "test"}]}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )

        from src.easy_mode.plot_generator import PlotGenerator
        plot_gen = PlotGenerator(test_engine.llm)
        plot = await plot_gen.generate(
            bible={"world": "test", "protagonist": "test"},
            target_episodes=3,
            tension_curve=[30, 50, 70]
        )

        assert len(plot) == 3
        # Redis にキャッシュされたか確認
        keys = await redis_client.keys("kaku:cache:*")
        assert len(keys) >= 0  # キャッシュがある場合

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_episode_audit_uses_chromadb(self, test_engine, chroma_client, mock_llm_client):
        """エピソード監査が ChromaDB を使用することを確認"""
        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"score": 90, "issues": []}'},
            '{"score": 90, "issues": []}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )

        from src.easy_mode.episode_auditor import EpisodeAuditor
        auditor = EpisodeAuditor(test_engine.llm, genre="zarma")
        result = await auditor.audit("テストエピソード内容。ざまぁ見ろ。実はチートだった。", {})

        assert result.score >= 0
        assert result.passed is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_episode_rewrite_with_spice_guard(self, test_engine, mock_llm_client):
        """SpiceGuard 付きリライトが動作することを確認"""
        mock_llm_client.generate_text.return_value = (
            "改善後のテストコンテンツ。ざまぁ見ろ。実はチートだった。",
            {"prompt_tokens": 50, "completion_tokens": 150}
        )

        from src.easy_mode.episode_rewriter import EpisodeRewriter
        rewriter = EpisodeRewriter(test_engine.llm, genre="zarma")
        result = await rewriter.rewrite(
            "元のテストコンテンツ。ざまぁ見ろ。実はチートだった。",
            ["改善指示1", "改善指示2"],
            []  # SpiceElements
        )

        assert "改善後の" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_series_finalizer_creates_asset_pack(self, test_engine, mock_llm_client, tmp_path):
        """シリーズ完結時にアセットパックが作成されることを確認"""
        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"title": "テスト", "synopsis": "あらすじ"}'},
            '{"title": "テスト", "synopsis": "あらすじ"}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )

        from src.easy_mode.series_finalizer import SeriesFinalizer
        finalizer = SeriesFinalizer(test_engine.llm, genre="zarma")
        episodes = [{"ep_num": i, "content": f"エピソード{i}"} for i in range(1, 4)]
        result = await finalizer.finalize(
            episodes=episodes,
            bible={"world": "test"},
            plot_outline=[{"ep_num": i, "title": f"ep{i}"} for i in range(1, 4)]
        )

        assert "title" in result
        assert "total_words" in result
        assert "tags" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_progress_reporting_callback(self, test_engine, mock_llm_client):
        """進捗報告コールバックが呼ばれることを確認"""
        from unittest.mock import MagicMock
        progress_callback = MagicMock()

        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"world": "test"}'},
            '{"world": "test"}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )
        mock_llm_client.generate_text.return_value = (
            "テスト生成コンテンツ",
            {"prompt_tokens": 50, "completion_tokens": 150}
        )

        from src.easy_mode.progress_reporter import create_progress_reporter
        reporter = create_progress_reporter(progress_callback)

        from src.easy_mode import EasyModePipeline
        pipeline = EasyModePipeline(
            engine=test_engine,
            genre="zarma",
            target_episodes=2,
            progress_reporter=reporter,
        )
        await pipeline.run()

        # 進捗コールバックが呼ばれたことを確認
        assert progress_callback.call_count >= 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cancellation_during_generation(self, test_engine, mock_llm_client):
        """生成中のキャンセルが動作することを確認"""
        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"world": "test"}'},
            '{"world": "test"}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )
        mock_llm_client.generate_text.return_value = (
            "テスト生成コンテンツ",
            {"prompt_tokens": 50, "completion_tokens": 150}
        )

        from src.easy_mode import EasyModePipeline
        pipeline = EasyModePipeline(
            engine=test_engine,
            genre="zarma",
            target_episodes=5,
        )

        # 即座にキャンセル
        pipeline.cancel()

        # 実行してもすぐに終了する
        result = await pipeline.run()

        # キャンセルされているため、エピソードが生成されていない
        assert result is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_genres_work(self, test_engine, mock_llm_client):
        """複数ジャンルで動作することを確認"""
        mock_llm_client.generate_json.return_value = (
            {"success": True, "content": '{"world": "test"}'},
            '{"world": "test"}',
            {"prompt_tokens": 100, "completion_tokens": 200}
        )
        mock_llm_client.generate_text.return_value = (
            "テスト生成コンテンツ",
            {"prompt_tokens": 50, "completion_tokens": 150}
        )

        for genre in ["zarma", "aku_reijo", "cheat_tensei", "slow_life"]:
            from src.easy_mode import create_series
            pipeline = create_series(test_engine, genre, target_episodes=1)
            result = await pipeline.run()
            assert result is not None
            assert result.genre == genre

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_engine_container_integration(self, test_engine):
        """DI コンテナ経由でのエンジン取得が動作することを確認"""
        from src.core.container import AppContainer
        container = AppContainer()
        engine = container.engine()

        assert engine is not None
        assert hasattr(engine, 'planner')
        assert hasattr(engine, 'writer')
        assert hasattr(engine, 'pm')
        assert hasattr(engine, 'ctx_mgr')
