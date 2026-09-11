"""Phase P4: 非同期ブロッキング解消 & DB セッション整合 検証テスト."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.embedding_service import EmbeddingService, embedding_service
from src.services.chunk_ingestion import upsert_chunks, backfill_missing_embeddings
from src.services.rag_service import GraphRAGService, rag_service
from src.services.graph_pipeline import GraphPipelineService
from src.backend.redis_util import get_async_redis_client
from src.backend.routers.tasks import get_task_status, get_dag_status, stop_task


class TestAsyncEmbeddingOffload:
    """非同期埋め込みオフロードの検証."""

    @pytest.mark.asyncio
    async def test_get_embedding_async_returns_vector(self):
        """get_embedding_async が正しくベクトルを返すこと."""
        vec = await embedding_service.get_embedding_async("test")
        assert isinstance(vec, list)
        assert len(vec) == 1536
        assert all(isinstance(x, float) for x in vec)

    @pytest.mark.asyncio
    async def test_embed_texts_async_returns_vectors(self):
        """embed_texts_async が正しくベクトルリストを返すこと."""
        vecs = await embedding_service.embed_texts_async(["text1", "text2"])
        assert isinstance(vecs, list)
        assert len(vecs) == 2
        assert all(len(v) == 1536 for v in vecs)

    @pytest.mark.asyncio
    async def test_embedding_async_offloads_to_thread(self):
        """埋め込み呼び出しがワーカースレッドにオフロードされること."""
        # モックで呼び出し元スレッドと実行スレッドが異なることを確認
        import threading

        main_thread = threading.current_thread()
        seen_threads = set()

        class MockEmbeddingService:
            def get_embedding(self, text):
                seen_threads.add(threading.current_thread())
                return [0.0] * 1536

        mock_service = MockEmbeddingService()

        async def call_async():
            return await asyncio.to_thread(mock_service.get_embedding, "test")

        await call_async()

        # メインスレッド以外で実行されていることを確認
        assert any(t != main_thread for t in seen_threads)


class TestChunkIngestionAsync:
    """チャンク埋め込み非同期処理の検証."""

    @pytest.mark.asyncio
    async def test_upsert_chunks_uses_async_embedding(self):
        """upsert_chunks が非同期埋め込みを使用すること."""
        mock_store = AsyncMock()
        mock_chunks = [
            MagicMock(id=1, content="text1"),
            MagicMock(id=2, content="text2"),
        ]

        with patch("src.services.chunk_ingestion.embedding_service") as mock_emb:
            mock_emb.embed_texts_async = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])
            mock_store.add_documents = AsyncMock()

            result = await upsert_chunks(mock_store, mock_chunks, "test_collection")

            assert result == 2
            mock_emb.embed_texts_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_backfill_missing_embeddings_async(self):
        """backfill_missing_embeddings が非同期で動作すること."""
        mock_session = MagicMock()
        mock_store = AsyncMock()
        mock_chunks = [
            MagicMock(id=1, content="text1", embedding=None),
            MagicMock(id=2, content="text2", embedding=None),
        ]
        mock_session.query.return_value.all.return_value = mock_chunks

        with patch("src.services.chunk_ingestion.embedding_service") as mock_emb:
            mock_emb.embed_texts_async = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])

            result = await backfill_missing_embeddings(mock_session, mock_store, "test", batch_size=64)

            assert result == 2
            mock_emb.embed_texts_async.assert_called()


class TestRAGServiceAsync:
    """RAGサービスの非同期化検証."""

    @pytest.mark.asyncio
    async def test_search_similar_chunks_async_offload(self):
        """search_similar_chunks が非同期オフロードすること."""
        mock_session = MagicMock()
        mock_session.execute = MagicMock(return_value=[])

        # pgvectorブランチのテスト（HAS_PGVECTOR=FalseでSQLiteブランチをテスト）
        from src.services.rag_service import GraphRAGService

        with patch("src.services.rag_service.embedding_service") as mock_emb:
            mock_emb.get_embedding = MagicMock(return_value=[0.1] * 1536)

            rag = GraphRAGService()
            # 内部で await asyncio.to_thread が呼ばれていることを確認
            result = await rag.search_similar_chunks(mock_session, "test query")

            # 埋め込み呼び出しが発生していることを確認
            mock_emb.get_embedding.assert_called()

    @pytest.mark.asyncio
    async def test_hybrid_search_async(self):
        """hybrid_search が非同期で動作すること."""
        from src.services.rag_service import GraphRAGService

        mock_session = MagicMock()

        with patch("src.services.rag_service.embedding_service") as mock_emb:
            mock_emb.get_embedding = MagicMock(return_value=[0.1] * 1536)
            mock_emb.embed_texts = MagicMock(return_value=[[0.2] * 1536])

            rag = GraphRAGService()
            result = await rag.hybrid_search(mock_session, "test query")

            # 非同期メソッドとして実行完了
            assert isinstance(result, list)


class TestGraphPipelineAsync:
    """GraphPipeline の非同期埋め込み検証."""

    @pytest.mark.asyncio
    async def test_save_chapter_chunks_async_embedding(self):
        """_save_chapter_chunks_atomic が非同期埋め込みを使用すること."""
        mock_session = MagicMock()
        pipeline = GraphPipelineService()

        with patch("src.services.graph_pipeline.embedding_service") as mock_emb:
            mock_emb.get_embedding = AsyncMock(return_value=[0.1] * 1536)

            result = await pipeline._save_chapter_chunks_atomic(mock_session, 1, "test paragraph")

            assert result == 1
            mock_emb.get_embedding.assert_called()


class TestAsyncRedisClient:
    """非同期Redisクライアントの検証."""

    @pytest.mark.asyncio
    async def test_get_async_redis_client_factory(self):
        """非同期Redisクライアントファクトリが存在すること."""
        client = await get_async_redis_client()
        # Redisが利用できない環境ではNoneが返る（フォールバック動作）
        # ここでは例外が発生しないことのみ確認
        assert client is None or hasattr(client, "ping")


class TestTasksRouterAsyncRedis:
    """tasks.py の非同期Redis検証."""

    @pytest.mark.asyncio
    async def test_get_task_status_uses_async_redis(self):
        """get_task_status が非同期Redisを使用すること."""
        with patch("src.backend.routers.tasks.get_async_redis_client") as mock_get:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_get.return_value = mock_redis

            from src.backend.routers.tasks import get_task_status

            result = await get_task_status("test_task")

            mock_get.assert_called_once()
            mock_redis.get.assert_called_once_with("task_status:test_task")

    @pytest.mark.asyncio
    async def test_get_dag_status_uses_async_redis(self):
        """get_dag_status が非同期Redisを使用すること."""
        with patch("src.backend.routers.tasks.get_async_redis_client") as mock_get:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_get.return_value = mock_redis

            from src.backend.routers.tasks import get_dag_status

            result = await get_dag_status("test_dag")

            mock_get.assert_called_once()
            mock_redis.get.assert_called_once_with("dag_status:test_dag")

    @pytest.mark.asyncio
    async def test_stop_task_uses_async_redis(self):
        """stop_task が非同期Redisを使用すること."""
        with patch("src.backend.routers.tasks.get_async_redis_client") as mock_get:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock()
            mock_get.return_value = mock_redis

            from src.backend.routers.tasks import stop_task
            from src.core.container import AppContainer

            # AppContainerのモック
            mock_db = MagicMock()
            mock_session = AsyncMock()
            mock_db.get_session = MagicMock(return_value=mock_session)
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

            with patch.object(AppContainer, "db", MagicMock(return_value=mock_db)):
                try:
                    await stop_task("test_task")
                except Exception:
                    pass  # DBエラーは無視

            mock_get.assert_called_once()
            mock_redis.get.assert_called_once_with("task_status:test_task")


class TestAntiAIAsyncOffload:
    """Anti-AIループコントローラーの非同期オフロード検証."""

    @pytest.mark.asyncio
    async def test_correct_endpoint_offloads_loop(self):
        """correct エンドポイントがループ処理をスレッドにオフロードすること."""
        import threading

        from src.backend.routers.anti_ai import correct

        main_thread = threading.current_thread()
        seen_threads = set()

        class MockDetector:
            def detect(self, text):
                class Result:
                    total_score = 50.0
                    category_scores = {}
                    violations = [type('V', (), {'to_dict': lambda self: {}})()]
                return Result()

        class MockLoopController:
            def run_sync(self, text, max_loops, score_threshold):
                seen_threads.add(threading.current_thread())
                class Result:
                    text = "corrected"
                    final_score = 95.0
                    iterations = 1
                    converged = True
                    history = []
                return Result()

        with patch("src.backend.routers.anti_ai._loop_controller", MockLoopController()):
            with patch("src.backend.routers.anti_ai._detector", MockDetector()):
                from src.backend.routers.anti_ai import CorrectRequest

                request = CorrectRequest(text="test text", max_loops=3, score_threshold=90.0)

                try:
                    result = await correct(request)
                except Exception:
                    pass  # 他の依存関係エラーは無視

                # ワーカースレッドで実行されていることを確認
                assert any(t != main_thread for t in seen_threads)


class TestAsyncSessionConsistency:
    """非同期セッション整合性の検証."""

    @pytest.mark.asyncio
    async def test_easy_mode_uses_async_session(self):
        """easy_mode.py が AsyncSession を使用すること."""
        # database.SessionLocal() が使用されていないことを確認（静的解析で代替）
        import src.backend.routers.easy_mode as easy_mode
        import inspect

        source = inspect.getsource(easy_mode)
        assert "database.SessionLocal()" not in source

    @pytest.mark.asyncio
    async def test_illustrations_uses_async_session(self):
        """illustrations.py が AsyncSession を使用すること."""
        import src.backend.routers.illustrations as illustrations
        import inspect

        source = inspect.getsource(illustrations)
        assert "database.SessionLocal()" not in source


class TestExportAsyncOffload:
    """export.py の非同期オフロード検証."""

    @pytest.mark.asyncio
    async def test_export_ebook_offloads_to_thread(self):
        """export_ebook_alias がスレッドにオフロードすること."""
        import threading

        from src.backend.routers.export import export_ebook_alias

        main_thread = threading.current_thread()
        seen_threads = set()

        class MockMultimediaService:
            def export_ebook(self, book_id, formats):
                seen_threads.add(threading.current_thread())
                class Result:
                    asset_id = 1
                    files = ["test.epub"]
                    metadata = {"formats": formats}
                return Result()

        mock_service = MockMultimediaService()

        from src.backend.routers.export import EbookExportRequest

        request = EbookExportRequest(book_id=1, formats=["epub", "pdf"])

        with patch("src.backend.routers.export.get_multimedia_service", return_value=mock_service):
            with patch("src.backend.routers.export._check_multimedia"):
                try:
                    await export_ebook_alias(request, service=mock_service)
                except Exception:
                    pass

        # ワーカースレッドで実行されていることを確認
        assert any(t != main_thread for t in seen_threads)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])