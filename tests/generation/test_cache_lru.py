"""
Regression tests for Step 12: LRU eviction and memory bounds in GenerationCache.
Verifies that:
1. GenerationCache respects max_size limit and evicts oldest items.
2. Accessing an item with get() updates its LRU position so it is not evicted first.
3. Updating an existing item with set() refreshes its LRU position.
4. Stats include max_size and accurate size.
5. Thread-safety under concurrent access.
"""

import threading
from src.generation.cache import GenerationCache


def test_cache_lru_eviction_basic():
    # Cache with capacity 3
    cache = GenerationCache(max_size=3)

    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")

    assert cache.stats()["size"] == 3

    # Add 4th item, oldest "a" should be evicted
    cache.set("d", "4")

    assert cache.stats()["size"] == 3
    found_a, val_a = cache.get("a")
    assert not found_a
    assert val_a is None

    # b, c, d should still be present
    assert cache.get("b")[0]
    assert cache.get("c")[0]
    assert cache.get("d")[0]


def test_cache_lru_get_refreshes_order():
    cache = GenerationCache(max_size=3)

    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")

    # Access "a", making it most recently used. New LRU order is b -> c -> a
    found, val = cache.get("a")
    assert found and val == "1"

    # Insert "d", which should evict "b" (now the oldest)
    cache.set("d", "4")

    # "b" was evicted
    assert not cache.get("b")[0]

    # "a", "c", "d" remain
    assert cache.get("a")[0]
    assert cache.get("c")[0]
    assert cache.get("d")[0]


def test_cache_lru_set_overwrite_refreshes_order():
    cache = GenerationCache(max_size=3)

    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")

    # Overwrite "a", making it most recently used. New order: b -> c -> a
    cache.set("a", "updated_1")

    # Insert "d", which should evict "b"
    cache.set("d", "4")

    assert not cache.get("b")[0]
    assert cache.get("a") == (True, "updated_1")
    assert cache.get("c")[0]
    assert cache.get("d")[0]


def test_cache_stats_and_clear():
    cache = GenerationCache(max_size=5)
    cache.set("k1", "v1")
    cache.get("k1")  # Hit
    cache.get("k2")  # Miss

    stats = cache.stats()
    assert stats["size"] == 1
    assert stats["max_size"] == 5
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5

    cache.clear()
    assert cache.stats()["size"] == 0
    assert cache.stats()["hits"] == 0


def test_cache_concurrent_access():
    cache = GenerationCache(max_size=50)

    def worker(worker_id: int):
        for i in range(100):
            key = f"key_{worker_id}_{i % 20}"
            cache.set(key, f"val_{worker_id}_{i}")
            cache.get(key)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Size should be bounded by max_size
    assert cache.stats()["size"] <= 50
