"""100 チャンク規模のパフォーマンステスト.

InMemoryFallbackStore と EmbeddingService の組み合わせで実測値を測定.
``-m perf`` で実行可能 (`pytest -m perf`).
"""
from __future__ import annotations

import time

import pytest

from src.services.embedding_service import embedding_service
from src.services.vector_store import InMemoryFallbackStore

pytestmark = pytest.mark.perf


def _gen_texts(n: int) -> list[str]:
    return [f"これは自動生成されたテストドキュメント #{i} です。" * 5 for i in range(n)]


@pytest.mark.asyncio
async def test_100_chunks_add_and_search():
    store = InMemoryFallbackStore(max_items_per_collection=200)
    texts = _gen_texts(100)
    vectors = embedding_service.embed_texts(texts)
    assert len(vectors) == 100

    t0 = time.perf_counter()
    await store.add_documents(
        "perf",
        [str(i) for i in range(100)],
        texts,
        vectors,
    )
    add_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    results = await store.search("perf", vectors[0], top_k=10)
    search_time = time.perf_counter() - t1

    # Generous bounds; perf tests should not hard-fail CI on slow hardware.
    print(f"\n[perf] add_100: {add_time:.3f}s  search_top10: {search_time:.3f}s")
    assert len(results) == 10
    # Soft bounds (pytest.skip if exceeded on slow runners).
    if add_time > 5.0:
        pytest.skip(f"add_time too slow: {add_time:.3f}s")
    if search_time > 1.0:
        pytest.skip(f"search_time too slow: {search_time:.3f}s")
