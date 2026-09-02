"""テキスト埋め込み (Embedding) 取得サービスモジュール."""
from __future__ import annotations

import hashlib
import math
import threading
import time
from typing import Any, Protocol

from src.backend.config import settings
from src.backend.logging_config import get_logger

logger = get_logger("embedding_service")


class EmbeddingCache(Protocol):
    """埋め込み結果のキャッシュ抽象."""

    def get(self, key: str) -> list[float] | None: ...
    def set(self, key: str, value: list[float]) -> None: ...
    def info(self) -> dict[str, Any]: ...


class LRUEmbeddingCache:
    """プロセス内 LRU 埋め込みキャッシュ."""

    def __init__(self, maxsize: int = 2048) -> None:
        from cachetools import LRUCache

        self._store: LRUCache[str, list[float]] = LRUCache(maxsize=maxsize)
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, key: str) -> list[float] | None:
        v = self._store.get(key)
        with self._lock:
            if v is not None:
                self._hits += 1
            else:
                self._misses += 1
        return v

    def set(self, key: str, value: list[float]) -> None:
        self._store[key] = value

    def info(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "backend": "lru",
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": (self._hits / total) if total else 0.0,
            }


class RedisEmbeddingCache:
    """Redis ベースの埋め込みキャッシュ. 接続失敗時は LRU に自動フォールバック.

    Uses the standard synchronous ``redis.Redis`` client.
    """

    def __init__(self, redis_client: Any | None = None, prefix: str = "emb:") -> None:
        self._client: Any = redis_client
        if self._client is None:
            try:
                import redis  # type: ignore

                self._client = redis.Redis.from_url(
                    settings.REDIS_URL, socket_connect_timeout=1
                )
                self._client.ping()
            except Exception as e:
                logger.warning(
                    "Redis cache unavailable, falling back to in-memory LRU: %s", e
                )
                self._client = None
        self._prefix = prefix
        self._fallback = LRUEmbeddingCache()

    def get(self, key: str) -> list[float] | None:
        if self._client is None:
            return self._fallback.get(key)
        try:
            raw = self._client.get(self._prefix + key)
        except Exception as e:  # pragma: no cover
            logger.debug("Redis embedding cache get failed: %s", e)
            return self._fallback.get(key)
        if raw is None:
            return self._fallback.get(key)
        try:
            import json

            vec = json.loads(raw)
            if isinstance(vec, list) and all(isinstance(x, (int, float)) for x in vec):
                return [float(x) for x in vec]
        except Exception:
            return None
        return None

    def set(self, key: str, value: list[float]) -> None:
        self._fallback.set(key, value)
        if self._client is None:
            return
        try:
            import json

            self._client.set(self._prefix + key, json.dumps(value))
        except Exception as e:  # pragma: no cover
            logger.debug("Redis embedding cache set failed: %s", e)

    def info(self) -> dict[str, Any]:
        return {"backend": "redis+lru", **self._fallback.info()}


class EmbeddingService:
    """OpenAI / 互換 API によるテキスト埋め込み生成サービス."""

    _BATCH_SIZE: int = 64
    _RATE_LIMIT_SLEEP: float = 0.01  # 100 RPM rough budget

    def __init__(
        self,
        model_name: str | None = None,
        cache: EmbeddingCache | None = None,
    ) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._client: Any = None
        self._cache: EmbeddingCache = cache or LRUEmbeddingCache()
        self._lock = threading.Lock()

    def _get_client(self) -> Any:
        if self._client is None:
            if settings.OPENAI_API_KEY:
                from openai import OpenAI

                kwargs: dict[str, Any] = {"api_key": settings.OPENAI_API_KEY}
                if settings.OPENAI_BASE_URL:
                    kwargs["base_url"] = settings.OPENAI_BASE_URL
                self._client = OpenAI(**kwargs)
            else:
                self._client = None
        return self._client

    def _rate_limit_wait(self) -> None:
        time.sleep(self._RATE_LIMIT_SLEEP)

    @staticmethod
    def _key_for(text: str) -> str:
        return LRUEmbeddingCache._key(text)

    def get_embedding(self, text: str) -> list[float]:
        """指定されたテキストの 1536 次元ベクトルを取得する.

        空文字列 / 空白のみはゼロベクトル.
        結果は ``self._cache`` 経由でメモ化される.
        """
        if not text or not text.strip():
            return [0.0] * 1536
        key = self._key_for(text)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        results = self.get_embeddings_batch([text], batch_size=1)
        vec = results[0]
        self._cache.set(key, vec)
        return vec

    def get_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int | None = None,
    ) -> list[list[float]]:
        """複数テキストの埋め込みをバッチで取得する.

        空文字列 / 空白のみの入力は 1536 次元のゼロベクトルを返す.
        バッチサイズを超える場合は分割して呼び出す.
        既に ``self._cache`` にあるテキストはスキップして API コールを削減.
        """
        if not texts:
            return []

        size = batch_size or settings.RAG_BATCH_SIZE or self._BATCH_SIZE
        if size <= 0:
            size = self._BATCH_SIZE

        out: list[list[float]] = []
        to_fetch: list[tuple[int, str]] = []
        for i, t in enumerate(texts):
            if not t or not t.strip():
                out.append([0.0] * 1536)
                continue
            key = self._key_for(t)
            cached = self._cache.get(key)
            if cached is not None:
                out.append(cached)
            else:
                out.append([0.0])
                to_fetch.append((i, t))

        if not to_fetch:
            return out

        client = self._get_client()
        if client is not None:
            for chunk_start in range(0, len(to_fetch), size):
                chunk = to_fetch[chunk_start:chunk_start + size]
                api_inputs = [c[1] for c in chunk]
                self._rate_limit_wait()
                try:
                    response = client.embeddings.create(
                        input=api_inputs,
                        model=self.model_name,
                    )
                    indexed = sorted(response.data, key=lambda d: getattr(d, "index", 0))
                    api_results = [list(d.embedding) for d in indexed]
                except Exception as e:
                    logger.warning(
                        "OpenAI Embedding batch API failed: %s. Using pseudo-embeddings for chunk.",
                        e,
                    )
                    api_results = [self._generate_pseudo_embedding(t) for t in api_inputs]
                for (pos, text), vec in zip(chunk, api_results):
                    out[pos] = vec
                    self._cache.set(self._key_for(text), vec)
        else:
            for pos, text in to_fetch:
                vec = self._generate_pseudo_embedding(text)
                out[pos] = vec
                self._cache.set(self._key_for(text), vec)

        return out

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int | None = None,
    ) -> list[list[float]]:
        """``get_embeddings_batch`` の対称性エイリアス."""
        return self.get_embeddings_batch(texts, batch_size=batch_size)

    def cache_info(self) -> dict[str, Any]:
        return self._cache.info()

    def _generate_pseudo_embedding(self, text: str, dimension: int = 1536) -> list[float]:
        """テストやAPIキー未設定環境用の決定論的疑似埋め込みベクトル (正規化済み)."""
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        vec = []
        for i in range(dimension):
            val = math.sin(seed + i * 0.1)
            vec.append(val)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def __repr__(self) -> str:
        info = self._cache.info()
        return (
            f"EmbeddingService(model={self.model_name!r}, "
            f"cache_backend={info.get('backend')!r}, "
            f"hits={info.get('hits', 0)}, misses={info.get('misses', 0)})"
        )


embedding_service = EmbeddingService()


def embed_texts(
    texts: list[str],
    batch_size: int | None = None,
) -> list[list[float]]:
    """Module-level convenience over ``embedding_service.embed_texts``."""
    return embedding_service.embed_texts(texts, batch_size=batch_size)


__all__ = [
    "EmbeddingService",
    "EmbeddingCache",
    "LRUEmbeddingCache",
    "RedisEmbeddingCache",
    "embedding_service",
    "embed_texts",
]
