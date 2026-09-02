"""
kernels/memory.py - メモリ管理
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MemoryType(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working_memory"


@dataclass
class MemoryEntry:
    """メモリエントリ"""

    key: str
    value: Any
    memory_type: MemoryType = MemoryType.SHORT_TERM
    expires_at: float = 0.0
    created_at: float = 0.0

    def is_expired(self) -> bool:
        """期限切れか"""
        return time.time() > self.expires_at

    def update_ttl(self, ttl_seconds: float) -> None:
        """TTLを更新"""
        self.expires_at = time.time() + ttl_seconds


class MemoryManager:
    """
    メモリ管理システム
    """

    def __init__(self, storage_capacity: int = 1000):
        self.storage_capacity = storage_capacity
        self.store: dict[str, MemoryEntry] = {}
        self.phys_store: dict[str, list] = {}

    def store_short_term(self, key: str, value: Any, category: str = "general") -> None:
        """短期記憶に保存"""
        entry = MemoryEntry(key, value, MemoryType.SHORT_TERM)
        self.store[key] = entry

        # ストレージ容量管理
        if len(self.store) > self.storage_capacity:
            # 最古のアイテムを削除
            oldest_key = min(self.store.keys(), key=lambda k: self.store[k].created_at)
            del self.store[oldest_key]

    def store_long_term(self, key: str, value: Any, ttl_seconds: float = 86400) -> None:
        """長期記憶に保存"""
        entry = MemoryEntry(key, value, MemoryType.LONG_TERM, expires_at=time.time() + ttl_seconds)
        self.store[key] = entry

    def store_working_memory(self, key: str, value: Any) -> None:
        """作業記憶に保存"""
        self.store[key] = MemoryEntry(key, value, MemoryType.WORKING)

    def retrieve(self, key: str) -> Any | None:
        """値を取得"""
        entry = self.store.get(key)
        if entry and not entry.is_expired():
            return entry.value
        return None

    def delete(self, key: str) -> bool:
        """削除"""
        return key in self.store and self.store.pop(key)

    def clear(self) -> None:
        """全てをクリア"""
        self.store.clear()
        self.phys_store.clear()
