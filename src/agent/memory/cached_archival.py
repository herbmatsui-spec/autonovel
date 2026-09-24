"""Cached wrapper for ArchivalMemory to accelerate repeated semantic searches."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Optional

from src.agent.memory.archival_memory import ArchivalMemory
from src.agent.memory.interfaces import MemoryEntry
from src.stores.vector_store import VectorStore


class CachedArchivalMemory(ArchivalMemory):
    """LRUキャッシュを備えた ArchivalMemory"""

    def __init__(
        self,
        vector_store: VectorStore,
        max_cache_size: int = 100,
        **kwargs,
    ):
        super().__init__(vector_store=vector_store, **kwargs)
        self.max_cache_size = max_cache_size
        self._search_cache: OrderedDict[str, List[MemoryEntry]] = OrderedDict()
        self.cache_hits = 0
        self.cache_misses = 0

    def search(self, query: str, k: int = 5) -> List[MemoryEntry]:
        cache_key = f"{query}::k={k}"
        if cache_key in self._search_cache:
            self.cache_hits += 1
            self._search_cache.move_to_end(cache_key)
            return self._search_cache[cache_key]

        self.cache_misses += 1
        results = super().search(query, k=k)

        # LRU 管理
        self._search_cache[cache_key] = results
        if len(self._search_cache) > self.max_cache_size:
            self._search_cache.popitem(last=False)

        return results

    def insert(self, entry: MemoryEntry) -> None:
        super().insert(entry)
        # 挿入時はキャッシュクリア
        self._search_cache.clear()

    @property
    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total) if total > 0 else 0.0


__all__ = ["CachedArchivalMemory"]
