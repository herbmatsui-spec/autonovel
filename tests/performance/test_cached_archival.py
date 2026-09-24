"""Performance tests for CachedArchivalMemory."""
import time
from src.agent.memory.cached_archival import CachedArchivalMemory
from src.agent.memory.interfaces import MemoryEntry
from src.stores.vector_store import InMemoryVectorStore


def test_cache_hit_rate():
    store = InMemoryVectorStore()
    cached_archival = CachedArchivalMemory(vector_store=store, max_cache_size=50)

    # 100件のエントリを投入
    for i in range(100):
        cached_archival.insert(MemoryEntry(f"e_{i}", f"エピソード{i}におけるキャラクター同士の対話と感情"))

    # 1回目の検索（キャッシュミス）
    t0 = time.perf_counter()
    r1 = cached_archival.search("エピソード10", k=3)
    miss_time = (time.perf_counter() - t0) * 1000

    # 2回目の同一検索（キャッシュヒット）
    t1 = time.perf_counter()
    r2 = cached_archival.search("エピソード10", k=3)
    hit_time = (time.perf_counter() - t1) * 1000

    assert r1 == r2
    assert cached_archival.cache_hits == 1
    assert cached_archival.cache_misses == 1
    assert cached_archival.hit_rate == 0.5
    # ヒット時の方が高速であること
    assert hit_time <= miss_time + 1.0
