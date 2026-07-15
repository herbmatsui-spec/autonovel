"""プロンプトキャッシュ統合モジュール.

Gemini Context Caching (静的コンテンツキャッシュ) と
分散キャッシュ (Redis + ChromaDB セマンティックキャッシュ) を統合し、
統一的なインターフェースを提供する。
"""
import logging
from typing import Any, Dict, Optional

from cachetools import LRUCache
# コンテキストキャッシュの無効化（一時的な処置）
class CachedContent:
    pass

class CachingPlaceholder:
    CachedContent = CachedContent

caching = CachingPlaceholder()



from src.services.redis_cache import (
    PromptCacheService,
    RedisCacheService,
    close_cache_services,
    get_prompt_cache,
    get_redis_cache,
)
from src.services.semantic_cache import SemanticCacheManager

logger = logging.getLogger(__name__)


class PromptCacheManager:
    """
    Gemini Context Caching を管理するクラス。
    静的なプロンプトコンテンツをキャッシュし、API呼び出し時のコストとレイテンシを削減する。
    """
    def __init__(self):
        self._cache_map: Dict[str, caching.CachedContent] = {}

    def get_or_create_cache(
        self,
        cache_key: str,
        contents: list,
        model_name: str = "gemini-3.1-flash-lite",
        ttl_minutes: int = 60
    ) -> caching.CachedContent:
        """
        キャッシュが存在すれば取得、なければ作成する。
        contents: [{"role": "user", "parts": [...]}, ...] の形式を想定
        """
        if cache_key in self._cache_map:
            # 簡易チェック: TTLが切れていないかの確認などはGoogle SDKがよしなにやってくれることを期待するが
            # 必要であればここで期限チェックを行う
            return self._cache_map[cache_key]

        logger.info(f"Creating Context Cache: {cache_key}")
        # Note: 実際の実装では genai.caching.CachedContent.create を使用
        # モデル名やコンテンツの構造はAPI仕様に従う
        cache = caching.CachedContent.create(
            model=model_name,
            contents=contents,
            ttl=f"{ttl_minutes * 60}s"
        )
        self._cache_map[cache_key] = cache
        return cache

    def clear_cache(self, cache_key: str):
        if cache_key in self._cache_map:
            # API側の削除が必要な場合はここに記述
            del self._cache_map[cache_key]
            logger.info(f"Cleared Context Cache: {cache_key}")


class UnifiedPromptCache:
    """統合プロンプトキャッシュ.
    
    L1: インメモリ LRU (完全一致)
    L2: Redis 分散キャッシュ (完全一致)
    L3: ChromaDB セマンティックキャッシュ (類似検索)
    L4: Gemini Context Caching (静的システムプロンプト等)
    """

    def __init__(
        self,
        vector_store: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        redis_url: Optional[str] = None,
        l1_maxsize: int = 1000,
    ):
        # L1 インメモリキャッシュ
        self._l1_cache = LRUCache(maxsize=l1_maxsize)

        # L3 セマンティックキャッシュ (ChromaDB)
        self._semantic_cache = None
        if vector_store and llm_client:
            self._semantic_cache = SemanticCacheManager(vector_store, llm_client)

        # L2 Redis + 統合サービス (遅延初期化)
        self._redis_cache: Optional[RedisCacheService] = None
        self._prompt_cache: Optional[PromptCacheService] = None
        self._redis_url = redis_url

        # L4 Gemini Context Caching
        self._context_cache_manager = PromptCacheManager()

    async def _ensure_prompt_cache(self) -> PromptCacheService:
        """プロンプトキャッシュサービスを遅延初期化."""
        if self._prompt_cache is None:
            self._redis_cache = await get_redis_cache()  # シングルトン取得
            # URLが指定されている場合は再初期化が必要だが、シングルトンパターンでは最初の設定が優先される
            self._prompt_cache = await get_prompt_cache(
                semantic_cache=self._semantic_cache,
                l1_cache=self._l1_cache,
            )
        return self._prompt_cache

    async def get_cached_response(
        self,
        template_name: str,
        prompt: str,
        model_id: str,
        task_type: str = "generation",
        genre: str = "general",
        temperature: float = 0.7,
        template_version: str = "1.0",
        **params: Any
    ) -> Optional[Any]:
        """キャッシュから応答を取得 (L1 -> L2 -> L3 の順で検索)."""
        cache = await self._ensure_prompt_cache()
        return await cache.get(
            template_name=template_name,
            prompt=prompt,
            model_id=model_id,
            task_type=task_type,
            genre=genre,
            temperature=temperature,
            template_version=template_version,
            **params
        )

    async def cache_response(
        self,
        template_name: str,
        prompt: str,
        response: Any,
        model_id: str,
        task_type: str = "generation",
        genre: str = "general",
        temperature: float = 0.7,
        template_version: str = "1.0",
        ttl: Optional[int] = None,
        **params: Any
    ) -> None:
        """応答をキャッシュに保存 (L1, L2, L3 すべてに保存)."""
        cache = await self._ensure_prompt_cache()
        await cache.set(
            template_name=template_name,
            prompt=prompt,
            response=response,
            model_id=model_id,
            task_type=task_type,
            genre=genre,
            temperature=temperature,
            template_version=template_version,
            ttl=ttl,
            **params
        )

    # === Gemini Context Caching (L4) 用メソッド ===

    def get_or_create_context_cache(
        self,
        cache_key: str,
        contents: list,
        model_name: str = "gemini-3.1-flash-lite",
        ttl_minutes: int = 60
    ) -> caching.CachedContent:
        """Gemini Context Cache を取得または作成."""
        return self._context_cache_manager.get_or_create_cache(
            cache_key, contents, model_name, ttl_minutes
        )

    def clear_context_cache(self, cache_key: str):
        """Gemini Context Cache をクリア."""
        self._context_cache_manager.clear_cache(cache_key)

    # === 管理用メソッド ===

    async def invalidate_book_cache(self, book_id: int) -> int:
        """特定書籍のキャッシュを無効化."""
        cache = await self._ensure_prompt_cache()
        return await cache.invalidate_book(book_id)

    async def invalidate_template_cache(self, template_name: str) -> int:
        """特定テンプレートのキャッシュを無効化."""
        cache = await self._ensure_prompt_cache()
        return await cache.invalidate_template(template_name)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得."""
        cache = await self._ensure_prompt_cache()
        return await cache.get_stats()

    async def close(self):
        """リソースを解放."""
        await close_cache_services()
        self._prompt_cache = None
        self._redis_cache = None


# シングルトンインスタンス
_unified_cache_instance: Optional[UnifiedPromptCache] = None


async def get_unified_prompt_cache(
    vector_store: Optional[Any] = None,
    llm_client: Optional[Any] = None,
    redis_url: Optional[str] = None,
) -> UnifiedPromptCache:
    """統合プロンプトキャッシュのシングルトンインスタンスを取得."""
    global _unified_cache_instance
    if _unified_cache_instance is None:
        _unified_cache_instance = UnifiedPromptCache(
            vector_store=vector_store,
            llm_client=llm_client,
            redis_url=redis_url,
        )
    return _unified_cache_instance
