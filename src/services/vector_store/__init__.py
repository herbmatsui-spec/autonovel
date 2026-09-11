"""
src/services/vector_store - ベクトルストアパッケージ (分割後)
"""
from __future__ import annotations

import sys
import types
import logging
from typing import Any

from src.services.vector_store.base import (
    BaseVectorStore,
    VectorStoreProtocol,
    CollectionType,
    CollectionConfig,
    DEFAULT_COLLECTIONS,
)
from src.services.vector_store.in_memory import (
    InMemoryFallbackStore,
    _metadata_matches,
)
from src.services.vector_store.chroma import (
    ChromaClientProvider,
    ChromaVectorStore,
    HAS_CHROMA,
    HAS_BM25,
    chromadb,
)
from src.services.vector_store.pgvector import (
    PgVectorStore,
    HAS_PGVECTOR,
    _embedding_to_pgvector,
    create_async_engine,
    async_sessionmaker,
)

logger = logging.getLogger(__name__)

HAS_INMEM = True


def get_default_store(
    db_path: str | None = None,
    *,
    max_items_per_collection: int = 10000,
) -> BaseVectorStore:
    """Construct a default vector store based on environment / availability.

    Honors the ``AUTONOVEL_RAG_MODE`` env / settings:
      - "pgvector": always use PgVectorStore (raises if unavailable)
      - "chroma": always use ChromaVectorStore (raises if unavailable)
      - "memory": always use InMemoryFallbackStore
      - "auto"  : use PgVectorStore > ChromaVectorStore > InMemoryFallbackStore priority
    """
    import os
    from src.backend.config import settings

    mode = getattr(settings, "AUTONOVEL_RAG_MODE", "auto") or os.environ.get(
        "AUTONOVEL_RAG_MODE", "auto"
    )

    if mode == "pgvector" or (mode == "auto" and HAS_PGVECTOR):
        if not HAS_PGVECTOR:
            if mode == "pgvector":
                raise RuntimeError("AUTONOVEL_RAG_MODE=pgvector but pgvector is not installed")
        else:
            database_url = settings.DATABASE_URL
            if database_url.startswith("sqlite"):
                logger.warning(
                    "[VECTOR STORE] pgvector requires PostgreSQL, falling back to chroma/memory"
                )
            else:
                return PgVectorStore(
                    database_url=database_url,
                    dimension=getattr(settings, "PGVECTOR_DIMENSIONS", 1536),
                )

    if mode == "chroma" or (mode == "auto" and HAS_CHROMA):
        if not HAS_CHROMA:
            if mode == "chroma":
                raise RuntimeError("AUTONOVEL_RAG_MODE=chroma but chromadb is not installed")
        else:
            provider = ChromaClientProvider(db_path or settings.CHROMA_DB_PATH)
            return ChromaVectorStore(provider)

    if mode == "memory":
        return InMemoryFallbackStore(max_items_per_collection=max_items_per_collection, enable_graph=True)

    return InMemoryFallbackStore(max_items_per_collection=max_items_per_collection, enable_graph=True)


class DefaultVectorStore:
    """Wrapper / factory for backwards compatibility with legacy callers."""

    def __new__(cls, *args: Any, **kwargs: Any) -> BaseVectorStore:
        return get_default_store(*args, **kwargs)


# Backward compatibility and mock propagation module proxy
class _VectorStorePackage(types.ModuleType):
    """Module proxy that propagates mock patches (patch('src.services.vector_store.<attr>'))
    to the underlying submodules (chroma, pgvector, in_memory).
    """

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name in ("chromadb", "HAS_CHROMA", "logger", "HAS_BM25"):
            if "src.services.vector_store.chroma" in sys.modules:
                setattr(sys.modules["src.services.vector_store.chroma"], name, value)
        if name in ("create_async_engine", "async_sessionmaker", "HAS_PGVECTOR"):
            if "src.services.vector_store.pgvector" in sys.modules:
                setattr(sys.modules["src.services.vector_store.pgvector"], name, value)


sys.modules[__name__].__class__ = _VectorStorePackage

__all__ = [
    "BaseVectorStore",
    "DefaultVectorStore",
    "ChromaClientProvider",
    "ChromaVectorStore",
    "PgVectorStore",
    "InMemoryFallbackStore",
    "CollectionType",
    "CollectionConfig",
    "DEFAULT_COLLECTIONS",
    "HAS_CHROMA",
    "HAS_PGVECTOR",
    "HAS_BM25",
    "HAS_INMEM",
    "VectorStoreProtocol",
    "get_default_store",
    "chromadb",
    "create_async_engine",
    "async_sessionmaker",
    "logger",
]
