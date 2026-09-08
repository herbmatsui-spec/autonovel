"""
src/services/vector_store/base.py - ベクトルストア基底クラスと型定義
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """ベクトルデータベース操作の抽象基底クラス"""

    @abstractmethod
    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ):
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def search_with_score(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_by_id(self, collection_name: str, ids: list[str]):
        pass

    @abstractmethod
    async def clear_collection(self, collection_name: str):
        pass


class VectorStoreProtocol(Protocol):
    """Duck-typed protocol mirroring BaseVectorStore."""

    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None: ...

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    async def search_with_score(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]: ...

    async def delete_by_id(self, collection_name: str, ids: list[str]) -> None: ...

    async def clear_collection(self, collection_name: str) -> None: ...


class CollectionType(Enum):
    """ベクトルコレクションの種類定義"""

    SEMANTIC_CACHE = "semantic_cache"
    STYLE_MEMORY = "style_memory"
    WORLD_MEMORY = "world_memory"
    CHARACTER_MEMORY = "character_memory"
    NARRATIVE_MEMORY = "narrative_memory"
    EPISODE_MEMORY = "episode_memory"


class CollectionConfig(BaseModel):
    """コレクション設定"""

    name: str
    space: str = "cosine"
    description: str = ""
    metadata_schema: dict[str, Any] = Field(default_factory=dict)
    hnsw_params: dict[str, Any] = Field(
        default_factory=lambda: {
            "hnsw:construction_ef": 100,
            "hnsw:search_ef": 50,
            "hnsw:M": 16,
        }
    )

    def get_metadata(self) -> dict[str, Any]:
        """ChromaDB用のメタデータを生成"""
        meta = {"hnsw:space": self.space}
        meta.update(self.hnsw_params)
        meta["description"] = self.description
        return meta


DEFAULT_COLLECTIONS: dict[CollectionType, CollectionConfig] = {
    CollectionType.SEMANTIC_CACHE: CollectionConfig(
        name="semantic_cache",
        space="cosine",
        description="Semantic cache for prompt-response similarity matching",
        metadata_schema={
            "task_type": "str",
            "genre": "str",
            "temperature": "float",
            "input_length": "int",
            "is_json": "bool",
            "created_at": "str",
            "last_accessed": "str",
        },
    ),
    CollectionType.STYLE_MEMORY: CollectionConfig(
        name="style_memory",
        space="cosine",
        description="Writing style, prose samples, and tone references",
        metadata_schema={
            "style_key": "str",
            "genre": "str",
            "sample_type": "str",
            "quality_score": "float",
            "source_episode": "int",
            "created_at": "str",
        },
    ),
    CollectionType.WORLD_MEMORY: CollectionConfig(
        name="world_memory",
        space="cosine",
        description="World building, settings, lore, and rules",
        metadata_schema={
            "category": "str",
            "importance": "int",
            "tags": "str",
            "source_episode": "int",
            "created_at": "str",
        },
    ),
    CollectionType.CHARACTER_MEMORY: CollectionConfig(
        name="character_memory",
        space="cosine",
        description="Character profiles, arcs, relationships, and development",
        metadata_schema={
            "character_id": "str",
            "character_name": "str",
            "arc_stage": "str",
            "relationship_type": "str",
            "source_episode": "int",
            "created_at": "str",
        },
    ),
    CollectionType.NARRATIVE_MEMORY: CollectionConfig(
        name="narrative_memory",
        space="cosine",
        description="Narrative structures, scene patterns, pacing, and beats",
        metadata_schema={
            "narrative_type": "str",
            "genre": "str",
            "tension_level": "int",
            "episode_range": "str",
            "created_at": "str",
        },
    ),
    CollectionType.EPISODE_MEMORY: CollectionConfig(
        name="episode_memory",
        space="cosine",
        description="Full episode content for reference and consistency checking",
        metadata_schema={
            "book_id": "int",
            "episode_number": "int",
            "word_count": "int",
            "genre": "str",
            "major_events": "str",
            "created_at": "str",
        },
    ),
}

__all__ = [
    "BaseVectorStore",
    "VectorStoreProtocol",
    "CollectionType",
    "CollectionConfig",
    "DEFAULT_COLLECTIONS",
]
