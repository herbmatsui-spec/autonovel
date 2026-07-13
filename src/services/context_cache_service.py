"""
Context Caching Service - Gemini API のサーバーサイドキャッシュを管理する。
不変コンテンツ（ワールドバイブル、キャラクターDNA）をキャッシュし、
リクエストごとの入力トークン処理時間を削減する。

v4.0: 覇権エンジンの高速化基盤
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheEntry:
    """個別キャッシュエントリのメタデータ"""
    def __init__(self, cache_name: str, created_at: float, ttl_seconds: int):
        self.cache_name = cache_name
        self.created_at = created_at
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class ContextCacheManager:
    """Gemini Context Caching API のラッパー。
    
    ワールドバイブルやシステムプロンプトなどの不変コンテンツを
    サーバーサイドでキャッシュし、リクエストごとの入力トークン処理を最大80%削減する。
    """

    def __init__(self, client: Any, model_name: str):
        self.client = client
        self.model_name = model_name
        self._cache_registry: Dict[str, CacheEntry] = {}

    def _content_hash(self, content: str) -> str:
        """コンテンツのハッシュを生成（キャッシュキーの一部として使用）"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    async def get_or_create_cache(
        self,
        cache_key: str,
        contents: list,
        system_instruction: Optional[str] = None,
        ttl_minutes: int = 60
    ) -> Optional[str]:
        """
        キャッシュを取得。存在しなければ作成する。
        
        Args:
            cache_key: キャッシュの識別子
            contents: キャッシュするコンテンツのリスト
            system_instruction: システムプロンプト
            ttl_minutes: キャッシュのTTL（分）
            
        Returns: cached_content の名前（キャッシュID）、失敗時は None
        """
        # 既存キャッシュのチェック
        if cache_key in self._cache_registry:
            entry = self._cache_registry[cache_key]
            if not entry.is_expired():
                logger.info(f"[CACHE HIT] {cache_key}")
                return entry.cache_name
            else:
                logger.info(f"[CACHE EXPIRED] {cache_key}")
                del self._cache_registry[cache_key]

        # 新規作成
        try:
            from google.genai import types as genai_types

            from src.core.executor_manager import executor_manager
            cached_content = await executor_manager.run_io(
                self.client.caches.create,
                model=self.model_name,
                config=genai_types.CreateCachedContentConfig(
                    contents=contents,
                    system_instruction=system_instruction,
                    ttl=f"{ttl_minutes * 60}s",
                    display_name=cache_key
                )
            )
            self._cache_registry[cache_key] = CacheEntry(
                cache_name=cached_content.name,
                created_at=time.time(),
                ttl_seconds=ttl_minutes * 60
            )
            logger.info(f"[CACHE CREATED] {cache_key} -> {cached_content.name}")
            return cached_content.name
        except Exception as e:
            logger.warning(f"[CACHE ERROR] Failed to create cache for '{cache_key}': {e}")
            return None

    def invalidate(self, cache_key: str) -> None:
        """指定されたキャッシュエントリを無効化する"""
        if cache_key in self._cache_registry:
            logger.info(f"[CACHE INVALIDATED] {cache_key}")
            del self._cache_registry[cache_key]

    def invalidate_all(self) -> None:
        """全キャッシュエントリを無効化する"""
        count = len(self._cache_registry)
        self._cache_registry.clear()
        logger.info(f"[CACHE CLEARED] {count} entries invalidated")

    def get_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を返す"""
        now = time.time()
        active = sum(1 for e in self._cache_registry.values() if not e.is_expired())
        expired = len(self._cache_registry) - active
        return {
            "total_entries": len(self._cache_registry),
            "active": active,
            "expired": expired,
            "keys": list(self._cache_registry.keys())
        }
