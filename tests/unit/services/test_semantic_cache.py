"""src/services/semantic_cache.py (SemanticCacheManager) の単体テスト.

実クラス名は SemanticCacheService ではなく SemanticCacheManager であるため、
本テストは実装に合わせて書き直したもの。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.semantic_cache import SemanticCacheManager


_SENTINEL = object()


def make_manager(vector_store=_SENTINEL, client=_SENTINEL):
    mock_store = MagicMock()
    mock_store.search = AsyncMock(return_value=[])
    mock_store.add_documents = AsyncMock(return_value=None)
    mock_store.get_collection = MagicMock()
    return SemanticCacheManager(
        vector_store=mock_store if vector_store is _SENTINEL else vector_store,
        client=MagicMock() if client is _SENTINEL else client,
    )


class TestSemanticCacheManagerL1:
    """L1 完全一致インメモリキャッシュのテスト."""

    def setup_method(self):
        self.manager = make_manager()

    def test_get_l1_key_deterministic(self):
        k1 = self.manager._get_l1_key("prompt", "writing", "general", 0.7)
        k2 = self.manager._get_l1_key("prompt", "writing", "general", 0.7)
        assert k1 == k2
        assert len(k1) == 64

    def test_get_l1_key_differs(self):
        k1 = self.manager._get_l1_key("prompt", "writing", "general", 0.7)
        k2 = self.manager._get_l1_key("prompt", "writing", "general", 0.8)
        assert k1 != k2

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self):
        self.manager._l1_cache["key1"] = "cached response"
        self.manager._l1_cache_key = None
        # _get_l1_key を固定値にモックして L1 ヒットを検証
        self.manager._get_l1_key = lambda *a, **k: "key1"
        result = await self.manager.search("prompt", "writing")
        assert result == "cached response"

    @pytest.mark.asyncio
    async def test_search_no_store_or_client(self):
        manager = make_manager(vector_store=None, client=MagicMock())
        result = await manager.search("prompt", "writing")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_no_client(self):
        manager = make_manager(vector_store=MagicMock(), client=None)
        result = await manager.search("prompt", "writing")
        assert result is None


class TestSemanticCacheManagerEmbedding:
    """埋め込み生成（L2-Bキャッシュ）のテスト."""

    def setup_method(self):
        self.manager = make_manager()

    @pytest.mark.asyncio
    async def test_get_embedding_cache_hit(self):
        vec = [0.1, 0.2, 0.3]
        import hashlib

        text_hash = hashlib.sha256("hello".encode("utf-8")).hexdigest()
        self.manager._l2_embedding_cache[text_hash] = vec
        result = await self.manager._get_embedding("hello")
        assert result == vec

    @pytest.mark.asyncio
    async def test_get_embedding_success(self):
        mock_res = MagicMock()
        mock_res.embeddings = [MagicMock()]
        mock_res.embeddings[0].values = [0.5, 0.6]

        mock_client = MagicMock()
        mock_client.models.embed_content.return_value = mock_res
        manager = make_manager(client=mock_client)

        # executor_manager.run_cpu をモック
        from unittest.mock import patch

        with patch("src.core.executor_manager.executor_manager") as mock_em:
            mock_em.run_cpu = AsyncMock(return_value=mock_res)
            result = await manager._get_embedding("new text")
        assert result == [0.5, 0.6]
        assert len(manager._l2_embedding_cache) == 1

    @pytest.mark.asyncio
    async def test_get_embedding_failure(self):
        mock_client = MagicMock()
        mock_client.models.embed_content.side_effect = RuntimeError("API down")
        manager = make_manager(client=mock_client)

        from unittest.mock import patch

        with patch("src.core.executor_manager.executor_manager") as mock_em:
            mock_em.run_cpu = AsyncMock(side_effect=RuntimeError("API down"))
            result = await manager._get_embedding("text")
        assert result == []


class TestSemanticCacheManagerSearch:
    """search のベクトル検索フローのテスト."""

    def setup_method(self):
        self.store = MagicMock()
        self.store.search = AsyncMock(return_value=[])
        self.store.get_collection = MagicMock()
        # add_documents は asyncio.create_task で起動されるため Coroutine を返す必要がある
        self.store.add_documents = AsyncMock(return_value=None)
        self.manager = make_manager(vector_store=self.store)

    @pytest.mark.asyncio
    async def test_search_embedding_empty_returns_none(self):
        self.manager._get_embedding = AsyncMock(return_value=[])
        result = await self.manager.search("prompt", "writing")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        self.manager._get_embedding = AsyncMock(return_value=[0.1, 0.2])
        self.store.search = AsyncMock(return_value=[])
        result = await self.manager.search("prompt", "writing")
        assert result is None
        self.store.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_distance_above_threshold_skipped(self):
        self.manager._get_embedding = AsyncMock(return_value=[0.1, 0.2])
        # threshold=0.95 → max_distance=0.05。distance=0.5 は skip される
        self.store.search = AsyncMock(
            return_value=[{"distance": 0.5, "metadata": {"cached_response": "resp"}}]
        )
        result = await self.manager.search("prompt", "writing", threshold=0.95)
        assert result is None

    @pytest.mark.asyncio
    async def test_search_hit_within_threshold(self):
        self.manager._get_embedding = AsyncMock(return_value=[0.1, 0.2])
        # 実装は best_hit["id"]/["content"] を参照するためこれらのキーを含める
        self.store.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "content": "good resp",
                    "distance": 0.02,
                    "metadata": {"input_length": 6},
                }
            ]
        )
        result = await self.manager.search("prompt", "writing", threshold=0.95)
        assert result == "good resp"

    @pytest.mark.asyncio
    async def test_search_selects_best_distance(self):
        self.manager._get_embedding = AsyncMock(return_value=[0.1, 0.2])
        # input_length は ±50% フィルタに引っかからないよう6（prompt長と一致）にする
        self.store.search = AsyncMock(
            return_value=[
                {"id": "doc1", "content": "far", "distance": 0.03, "metadata": {"input_length": 6}},
                {"id": "doc2", "content": "near", "distance": 0.01, "metadata": {"input_length": 6}},
            ]
        )
        result = await self.manager.search("prompt", "writing", threshold=0.95)
        assert result == "near"

    @pytest.mark.asyncio
    async def test_search_is_json_response_parsed(self):
        self.manager._get_embedding = AsyncMock(return_value=[0.1, 0.2])
        self.store.search = AsyncMock(
            return_value=[
                {
                    "id": "doc1",
                    "content": '{"key": "value"}',
                    "distance": 0.01,
                    "metadata": {"input_length": 6, "is_json": True},
                }
            ]
        )
        result = await self.manager.search("prompt", "writing", threshold=0.95)
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_add_l1_cache_populated(self):
        # add() による L1 キャッシュ登録を検証（search は L1 登録を行わない実装）
        await self.manager.add("prompt", "resp", task_type="writing", genre="general", temperature=0.7)
        keys = list(self.manager._l1_cache.keys())
        assert len(keys) == 1
        # L1 ヒット（embeddingを生成しない）
        self.manager._get_embedding = AsyncMock(side_effect=AssertionError("should not be called"))
        result = await self.manager.search("prompt", "writing", genre="general", temperature=0.7)
        assert result == "resp"

    @pytest.mark.asyncio
    async def test_add_no_store_or_client(self):
        manager = make_manager(vector_store=None, client=None)
        await manager.add("p", "r", task_type="writing")
        # L1には登録されるが vector には進まない（例外なし）
        assert len(manager._l1_cache) == 1
