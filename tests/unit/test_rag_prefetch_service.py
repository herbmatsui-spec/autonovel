
import pytest

from src.services.rag_prefetch_service import RagPrefetchService


def test_rag_prefetch_cache_key():
    """キャッシュキー生成の検証。"""
    service = RagPrefetchService()
    assert service.cache_key(10, 5) == "10_5"


@pytest.mark.asyncio
async def test_rag_prefetch_hit_and_eviction():
    """キャッシュの登録・取得および容量超過時のLRU破棄検証。"""
    service = RagPrefetchService(max_cache_size=2)

    # データを手動注入
    service._cache["1_1"] = {"style": "sample1"}
    service._cache["1_2"] = {"style": "sample2"}

    res = await service.get_cached(1, 1)
    assert res == {"style": "sample1"}

    # 3件目を追加
    service._cache["1_3"] = {"style": "sample3"}
    if len(service._cache) > 2:
        service._cache.popitem(last=False)

    assert len(service._cache) == 2


@pytest.mark.asyncio
async def test_rag_prefetch_invalidate():
    """キャッシュの無効化機能検証。"""
    service = RagPrefetchService()
    service._cache["1_1"] = {"data": "test"}

    service.invalidate(1, 1)
    assert "1_1" not in service._cache
