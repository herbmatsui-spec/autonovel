"""
Testcontainers を使用した統合テスト例
"""


import pytest

from src.easy_mode import create_series


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
    async def test_chromadb_vector_store(self, chroma_client):
        """ChromaDB ベクトルストアの動作確認"""
        from src.services.vector_store import ChromaVectorStore

        vector_store = ChromaVectorStore(client=chroma_client)

        # テストデータ追加
        test_embeddings = [[0.1] * 384, [0.2] * 384]
        test_metadata = [
            {"text": "テスト文書1", "genre": "zarma"},
            {"text": "テスト文書2", "genre": "zarma"}
        ]
        test_ids = ["doc1", "doc2"]

        await vector_store.add(test_embeddings, test_metadata, test_ids)

        # 検索テスト
        query_embedding = [0.15] * 384
        results = await vector_store.search(query_embedding, k=2)

        assert len(results) == 2
        assert results[0]["metadata"]["genre"] == "zarma"


class TestRedisIntegration:
    """Redis 統合テスト"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_redis_rate_limiting(self, redis_client):
        """Redis レート制限の動作確認"""

        key = "test:rate_limit:ip:127.0.0.1"

        # 初回リクエスト
        count = await redis_client.incr(key)
        await redis_client.expire(key, 60)
        assert count == 1

        # 2回目
        count = await redis_client.incr(key)
        assert count == 2

        # TTL 確認
        ttl = await redis_client.ttl(key)
        assert 0 < ttl <= 60

        # クリーンアップ
        await redis_client.delete(key)


class TestPostgreSQLIntegration:
    """PostgreSQL 統合テスト"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_crud(self, db_manager):
        """データベース CRUD 操作確認"""
        from src.backend.database import DataRepository
        from src.models.api_schemas import BookCreate

        repo = DataRepository(db_manager)

        # 作成
        book_data = BookCreate(
            title="テスト小説",
            genre="zarma",
            target_episodes=8
        )
        book = await repo.create_book(book_data)
        assert book.id is not None
        assert book.title == "テスト小説"

        # 読み取り
        fetched = await repo.get_book(book.id)
        assert fetched.title == "テスト小説"

        # 更新
        from src.models.api_schemas import BookUpdate
        updated = await repo.update_book(book.id, BookUpdate(title="更新済み"))
        assert updated.title == "更新済み"

        # 削除
        await repo.delete_book(book.id)
        deleted = await repo.get_book(book.id)
        assert deleted is None


class TestSettingsIntegration:
    """設定統合テスト"""

    @pytest.mark.integration
    def test_settings_from_env(self, monkeypatch):
        """環境変数から設定読み込み"""
        monkeypatch.setenv("KAKU_DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("KAKU_MODEL_WRITING", "custom-model")
        monkeypatch.setenv("KAKU_MAX_CONCURRENT_API_CALLS", "10")

        from config.settings import get_settings, reset_settings
        reset_settings()

        settings = get_settings()
        assert settings.database_url == "postgresql+asyncpg://test:test@localhost/test"
        assert settings.model_writing == "custom-model"
        assert settings.max_concurrent_api_calls == 10


class TestMetricsIntegration:
    """メトリクス統合テスト"""

    @pytest.mark.integration
    def test_prometheus_metrics_format(self):
        """Prometheus メトリクス形式確認"""
        from src.backend.observability.metrics import (
            generate_latest,
            kaku_http_requests_total,
            kaku_novel_generation_tasks_total,
        )

        # メトリクス記録
        kaku_http_requests_total.labels(method="GET", path="/api/test", status="200").inc()
        kaku_novel_generation_tasks_total.labels(workflow_type="easy", status="completed").inc()

        # 形式確認
        output = generate_latest().decode("utf-8")
        assert "kaku_http_requests_total" in output
        assert "kaku_novel_generation_tasks_total" in output
        assert 'method="GET"' in output
        assert 'status="200"' in output


# ===================== テスト実行用メイン =====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
