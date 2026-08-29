"""consistency/cache.py - チェック結果キャッシュ"""
import time
import hashlib
import json
from typing import List, Optional

from src.consistency.findings import Finding
from src.consistency.checkers.base import CheckContext


class ConsistencyCache:
    def __init__(self, ttl: int = 300):
        self._cache: dict[str, tuple[float, List[Finding]]] = {}
        self.ttl = ttl

    def _make_key(self, context: CheckContext) -> str:
        # Simple key based on book_id, branch_id, ep_num, and a version hash
        # In practice, we'd hash the chapter contents
        data = f"{context.book_id}:{context.branch_id}:{context.ep_num}"
        return hashlib.md5(data.encode()).hexdigest()

    def get(self, context: CheckContext) -> Optional[List[Finding]]:
        key = self._make_key(context)
        if key in self._cache:
            timestamp, findings = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return findings
            else:
                del self._cache[key]
        return None

    def set(self, context: CheckContext, findings: List[Finding]):
        key = self._make_key(context)
        self._cache[key] = (time.time(), findings)

    def invalidate(self, context: CheckContext):
        key = self._make_key(context)
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        self._cache.clear()


# Global instance
_consistency_cache = ConsistencyCache()


def get_cache() -> ConsistencyCache:
    return _consistency_cache