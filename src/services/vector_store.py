import json
import logging
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Protocol, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import chromadb
    from chromadb.api import ClientAPI
else:
    ClientAPI = Any

logger = logging.getLogger(__name__)

try:
    import chromadb

    HAS_CHROMA = True
except Exception as e:
    logger.warning(
        f"[VECTOR STORE] Failed to import/initialize chromadb: {e}. "
        "Vector features (RAG) will be disabled, falling back to legacy SQLite style fragments."
    )
    HAS_CHROMA = False

try:
    from sqlalchemy import (
        text,
    )
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    HAS_PGVECTOR = True
except Exception as e:
    logger.warning(
        f"[VECTOR STORE] Failed to import pgvector: {e}. "
        "pgvector backend will be disabled."
    )
    HAS_PGVECTOR = False

try:
    from rank_bm25 import BM25Okapi

    HAS_BM25 = True
except Exception as e:
    logger.warning(
        f"[VECTOR STORE] Failed to import rank_bm25: {e}. BM25 hybrid search will be disabled."
    )
    HAS_BM25 = False

# InMemoryFallbackStore is always available (pure Python, no third-party deps).
HAS_INMEM = True


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
    """Duck-typed protocol mirroring BaseVectorStore.

    Use this for type hints where accepting either the abstract base or a
    runtime-compatible class is desired (e.g. tests injecting a stub).
    """

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

    async def delete_by_id(self, collection_name: str, ids: list[str]) -> None: ...

    async def clear_collection(self, collection_name: str) -> None: ...


class CollectionType(Enum):
    """ベクトルコレクションの種類定義"""

    SEMANTIC_CACHE = "semantic_cache"  # セマンティックキャッシュ（意味的類似検索）
    STYLE_MEMORY = "style_memory"  # 文体・文調メモリ（スタイルRAG）
    WORLD_MEMORY = "world_memory"  # 世界観・設定メモリ（世界観RAG）
    CHARACTER_MEMORY = "character_memory"  # キャラクター・プロットメモリ（キャラRAG）
    NARRATIVE_MEMORY = "narrative_memory"  # 物語・シーンメモリ（ナラティブRAG）
    EPISODE_MEMORY = "episode_memory"  # エピソード内容メモリ（本文RAG）


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


# デフォルトコレクション設定
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
            "sample_type": "str",  # "prose", "dialogue", "description", etc.
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
            "category": "str",  # "geography", "history", "magic_system", "technology", "culture", "rules"
            "importance": "int",  # 1-5
            "tags": "str",  # JSON array as string
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
            "arc_stage": "str",  # "introduction", "development", "climax", "resolution"
            "relationship_type": "str",  # "ally", "enemy", "mentor", "rival", "love_interest"
            "source_episode": "int",
            "created_at": "str",
        },
    ),
    CollectionType.NARRATIVE_MEMORY: CollectionConfig(
        name="narrative_memory",
        space="cosine",
        description="Narrative structures, scene patterns, pacing, and beats",
        metadata_schema={
            "narrative_type": "str",  # "beat", "scene", "arc", "foreshadowing", "payoff"
            "genre": "str",
            "tension_level": "int",  # 1-10
            "episode_range": "str",  # "1-5", "6-10", etc.
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
            "major_events": "str",  # JSON array as string
            "created_at": "str",
        },
    ),
}


class ChromaClientProvider:
    """
    ChromaDBクライアントのライフサイクルを管理するプロバイダー。
    シングルトンとして動作し、接続の再利用と遅延初期化を提供する。
    """

    def __init__(
        self,
        db_path: str = "./chroma_db",
        *,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self.db_path = db_path
        self.host = host
        self.port = port
        self._client: ClientAPI | None = None

    def get_client(self, retries: int = 3, base_delay: float = 0.5):
        """
        クライアントを返却する。未初期化の場合は初期化を行う。
        接続失敗時に再試行ロジックを実行する。
        """
        if self._client is not None:
            return self._client

        if not HAS_CHROMA:
            logger.warning(
                "[CHROMA PROVIDER] chromadb is not installed. Vector features will be disabled."
            )
            return None

        import time

        for attempt in range(retries):
            try:
                if self.host:
                    port = self.port or 8000
                    logger.info(
                        f"[CHROMA PROVIDER] Initializing ChromaDB HTTP client at {self.host}:{port} (Attempt {attempt + 1}/{retries})"
                    )
                    self._client = chromadb.HttpClient(host=self.host, port=port)
                else:
                    logger.info(
                        f"[CHROMA PROVIDER] Initializing ChromaDB client at {self.db_path} (Attempt {attempt + 1}/{retries})"
                    )
                    self._client = chromadb.PersistentClient(path=self.db_path)
                return self._client
            except Exception as e:
                delay = base_delay * (2**attempt)
                logger.error(
                    f"[CHROMA PROVIDER] Failed to initialize ChromaDB: {e}. Retrying in {delay}s..."
                )
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    logger.critical(
                        f"[CHROMA PROVIDER] All {retries} attempts to initialize ChromaDB failed."
                    )

        return None

    def close(self):
        """クライアントのリソースを解放する。"""
        if self._client:
            try:
                # PersistentClient に明示的な close がない場合があるが、
                # 将来的な実装やカスタムクリーンアップのために定義
                logger.info("[CHROMA PROVIDER] Closing ChromaDB client connections")
                self._client = None
            except Exception as e:
                logger.error(f"[CHROMA PROVIDER] Error during close: {e}")


class ChromaVectorStore(BaseVectorStore):
    """
    ChromaDB を使用したベクトルデータベース管理クラス。
    複数の独立したコレクション（インデックス構造）を管理し、
    用途別の最適化された検索を提供する。
    """

    def __init__(self, client_provider: ChromaClientProvider):
        self.client_provider = client_provider
        self._collections: dict[str, Any] = {}
        self._initialized_collections: set = set()
        # BM25インデックス: collection_name -> {"docs -> BM25Okapi, corpus_tokens -> List[List[str]], doc_ids -> List[str] }
        self._bm25_indexes: dict[str, dict[str, Any]] = {}

    @property
    def client(self):
        """プロバイダー経由でクライアントを取得する"""
        return self.client_provider.get_client()

    def initialize_collections(
        self, collection_types: list[CollectionType] | None = None
    ) -> dict[str, bool]:
        """
        指定されたコレクションタイプを初期化する。
        未指定の場合は全デフォルトコレクションを初期化。

        Returns:
            {collection_name: success} のマップ
        """
        if collection_types is None:
            collection_types = list(DEFAULT_COLLECTIONS.keys())

        results = {}
        for ctype in collection_types:
            config = DEFAULT_COLLECTIONS[ctype]
            success = self._ensure_collection(config)
            results[config.name] = success

        return results

    def _ensure_collection(self, config: CollectionConfig) -> bool:
        """コレクションの存在確認と作成（メタデータスキーマ付き）"""
        if not self.client:
            logger.error(f"[VECTOR STORE] No client available for collection '{config.name}'")
            return False

        if config.name in self._initialized_collections:
            return True

        try:
            # 既存コレクションのメタデータを確認
            try:
                existing = self.client.get_collection(name=config.name)
                existing_meta = existing.metadata or {}
                # HNSWパラメータが異なる場合は警告
                if existing_meta.get("hnsw:space") != config.space:
                    logger.warning(
                        f"[VECTOR STORE] Collection '{config.name}' has different space: {existing_meta.get('hnsw:space')} vs {config.space}"
                    )
            except Exception:
                # 存在しない場合は作成
                pass

            # メタデータ込みで取得または作成
            metadata = config.get_metadata()
            self._collections[config.name] = self.client.get_or_create_collection(
                name=config.name, metadata=metadata
            )
            self._initialized_collections.add(config.name)
            logger.info(
                f"[VECTOR STORE] Initialized collection '{config.name}' with space={config.space}"
            )
            return True
        except Exception as e:
            logger.error(f"[VECTOR STORE] Failed to initialize collection '{config.name}': {e}")
            return False

    def get_collection(self, name: str, metadata: dict[str, Any] | None = None):
        """コレクションを取得または作成する（後方互換性）"""
        if not self.client:
            return None
        if name not in self._collections:
            try:
                self._collections[name] = self.client.get_or_create_collection(
                    name=name, metadata=metadata
                )
            except Exception as e:
                logger.error(f"[VECTOR STORE] Failed to get/create collection {name}: {e}")
                return None
        return self._collections[name]

    def get_collection_config(self, collection_type: CollectionType) -> CollectionConfig:
        """コレクションタイプから設定を取得"""
        return DEFAULT_COLLECTIONS[collection_type]

    _CHROMA_MAX_BATCH = 416

    @staticmethod
    def _chunks_of(items: list, size: int) -> list[list]:
        return [items[i:i + size] for i in range(0, len(items), size)]

    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ):
        """ドキュメントをベクトルDBに追加する (ChromaDB のバッチ上限を超える場合は分割)."""
        collection = self.get_collection(collection_name)
        if not collection:
            logger.warning(
                f"[VECTOR STORE] Skipping add_documents: Collection '{collection_name}' not available."
            )
            return
        n = len(ids)
        for start in range(0, n, self._CHROMA_MAX_BATCH):
            end = start + self._CHROMA_MAX_BATCH
            chunk_ids = ids[start:end]
            chunk_docs = documents[start:end]
            chunk_embs = embeddings[start:end]
            chunk_metas = metadatas[start:end] if metadatas else None
            if chunk_metas is not None:
                collection.add(
                    ids=chunk_ids,
                    documents=chunk_docs,
                    embeddings=chunk_embs,
                    metadatas=chunk_metas,
                )
            else:
                collection.add(
                    ids=chunk_ids,
                    documents=chunk_docs,
                    embeddings=chunk_embs,
                )
        logger.info(f"[VECTOR STORE] Added {n} documents to collection '{collection_name}'")

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """ベクトル類似度検索を実行する"""
        collection = self.get_collection(collection_name)
        if not collection:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                output.append(
                    {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                    }
                )
        return output

    async def search_with_score(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """スコア閾値付き検索（コサイン類似度ベース）"""
        results = await self.search(collection_name, query_embedding, top_k, where)

        # コサイン距離を類似度スコアに変換
        filtered = []
        for r in results:
            similarity = 1.0 - r.get("distance", 1.0)
            if similarity >= min_score:
                r["similarity"] = similarity
                filtered.append(r)

        # 類似度降順でソート
        filtered.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return filtered

    async def delete_by_id(self, collection_name: str, ids: list[str]):
        """指定したIDのドキュメントを削除する"""
        collection = self.get_collection(collection_name)
        if not collection:
            return
        collection.delete(ids=ids)
        logger.info(
            f"[VECTOR STORE] Deleted {len(ids)} documents from collection '{collection_name}'"
        )

    async def clear_collection(self, collection_name: str):
        """コレクションを空にする"""
        if not self.client:
            return
        try:
            self.client.delete_collection(name=collection_name)
        except Exception as e:
            logger.debug(f"[VECTOR STORE] Safe delete collection failed or was not found: {e}")
        if collection_name in self._collections:
            del self._collections[collection_name]
        if collection_name in self._initialized_collections:
            self._initialized_collections.remove(collection_name)
        logger.info(f"[VECTOR STORE] Cleared collection '{collection_name}'")

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """コレクションの統計情報を取得"""
        collection = self.get_collection(collection_name)
        if not collection:
            return {"count": 0, "error": "Collection not found"}

        try:
            count = collection.count()
            return {"count": count, "name": collection_name}
        except Exception as e:
            logger.debug(
                f"[VECTOR STORE] collection.count() failed, falling back to peek: {e}"
            )
            try:
                peeked = collection.peek(limit=1)
                exists = bool(peeked and peeked.get("ids"))
                return {"count": -1 if not exists else 1, "name": collection_name}
            except Exception as e2:
                logger.error(
                    f"[VECTOR STORE] Failed to get stats for '{collection_name}': {e2}"
                )
                return {"count": 0, "error": str(e2)}

    def list_collections(self) -> list[str]:
        """初期化済みコレクションの一覧を取得"""
        return list(self._initialized_collections)

    def audit_collection_coverage(
        self, collection_types: list[CollectionType] | None = None
    ) -> dict[str, bool]:
        """すべてのデフォルト CollectionType を初期化し、成否を返す.

        Returns:
            {CollectionType.name: success_bool} のマップ
        """
        if collection_types is None:
            collection_types = list(DEFAULT_COLLECTIONS.keys())
        return self.initialize_collections(collection_types)

    def _build_bm25_index(self, collection_name: str, documents: list[str], doc_ids: list[str]):
        """BM25インデックスを構築または更新する"""
        if not HAS_BM25:
            logger.warning("[VECTOR STORE] BM25 not available, skipping index build")
            return

        # ドキュメントをトークン化（簡易的な日本語対応：文字単位 + スペース区切り）
        def tokenize(text: str) -> list[str]:
            # 日本語文字と英数字を分離してトークン化
            import re

            # 英数字の単語 + 日本語文字（ひらがな、カタカナ、漢字）
            tokens = re.findall(
                r"[a-zA-Z0-9]+|[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", text.lower()
            )
            # さらに文字単位でも分割（日本語の部分一致対応）
            char_tokens = list(text.lower())
            return tokens + char_tokens

        corpus_tokens = [tokenize(doc) for doc in documents]
        bm25 = BM25Okapi(corpus_tokens)

        self._bm25_indexes[collection_name] = {
            "bm25": bm25,
            "corpus_tokens": corpus_tokens,
            "doc_ids": doc_ids,
            "documents": documents,
        }
        logger.info(
            f"[VECTOR STORE] Built BM25 index for collection '{collection_name}' with {len(documents)} documents"
        )

    async def add_documents_with_bm25(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ):
        """ドキュメントをベクトルDBに追加し、BM25インデックスも更新する"""
        # 通常のベクトル追加
        await self.add_documents(collection_name, ids, documents, embeddings, metadatas)

        # BM25インデックスの更新
        if HAS_BM25 and collection_name in self._bm25_indexes:
            # 既存インデックスに追加
            existing = self._bm25_indexes[collection_name]
            all_docs = existing["documents"] + documents
            all_ids = existing["doc_ids"] + ids
            self._build_bm25_index(collection_name, all_docs, all_ids)
        elif HAS_BM25:
            # 新規インデックス作成
            self._build_bm25_index(collection_name, documents, ids)

    async def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        alpha: float = 0.5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        ハイブリッド検索: ベクトル類似度検索 + BM25キーワード検索

        Args:
            collection_name: 検索対象コレクション名
            query_text: 検索クエリテキスト（BM25用）
            query_embedding: 検索クエリベクトル（ベクトル検索用）
            top_k: 取得件数
            where: メタデータフィルタ
            alpha: ベクトル検索の重み (0.0-1.0)。1.0でベクトルのみ、0.0でBM25のみ
            min_score: 結合スコアの最小閾値

        Returns:
            結合スコア順の検索結果リスト
        """
        # alpha clamp with warning
        if alpha < 0.0 or alpha > 1.0:
            logger.warning(
                f"[VECTOR STORE] hybrid_search alpha={alpha} out of [0,1], clamping."
            )
            alpha = max(0.0, min(1.0, alpha))
        # ベクトル検索（より多く取得して後でフィルタリング）
        vector_results = await self.search_with_score(
            collection_name, query_embedding, top_k * 3, where, min_score=0.0
        )

        # BM25検索
        bm25_results = []
        if HAS_BM25 and collection_name in self._bm25_indexes:
            bm25_data = self._bm25_indexes[collection_name]
            bm25 = bm25_data["bm25"]
            doc_ids = bm25_data["doc_ids"]
            documents = bm25_data["documents"]

            # クエリをトークン化
            def tokenize(text: str) -> list[str]:
                import re

                tokens = re.findall(
                    r"[a-zA-Z0-9]+|[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", text.lower()
                )
                char_tokens = list(text.lower())
                return tokens + char_tokens

            query_tokens = tokenize(query_text)
            bm25_scores = bm25.get_scores(query_tokens)

            # 上位候補を取得
            top_indices = sorted(
                range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True
            )[: top_k * 3]

            # BM25スコアを正規化 (0-1)
            max_bm25 = max(bm25_scores) if bm25_scores else 1.0
            min_bm25 = min(bm25_scores) if bm25_scores else 0.0
            bm25_range = max_bm25 - min_bm25 if max_bm25 > min_bm25 else 1.0

            for idx in top_indices:
                if bm25_scores[idx] <= 0:
                    continue
                normalized_bm25 = (bm25_scores[idx] - min_bm25) / bm25_range
                bm25_results.append(
                    {
                        "id": doc_ids[idx],
                        "content": documents[idx],
                        "bm25_score": bm25_scores[idx],
                        "normalized_bm25": normalized_bm25,
                        "metadata": {},  # メタデータは別途取得が必要な場合がある
                    }
                )

        # 結果を結合
        # ベクトル結果をIDでマップ化
        vector_map = {r["id"]: r for r in vector_results}
        bm25_map = {r["id"]: r for r in bm25_results}
        all_ids = set(vector_map.keys()) | set(bm25_map.keys())

        combined_results = []
        for doc_id in all_ids:
            vector_result = vector_map.get(doc_id)
            bm25_result = bm25_map.get(doc_id)

            vector_sim = vector_result.get("similarity", 0.0) if vector_result else 0.0
            bm25_norm = bm25_result.get("normalized_bm25", 0.0) if bm25_result else 0.0

            # 結合スコア: alpha * vector_sim + (1 - alpha) * bm25_norm
            combined_score = alpha * vector_sim + (1.0 - alpha) * bm25_norm

            if combined_score >= min_score:
                # ベクトル検索のメタデータを優先して使用
                metadata = vector_result.get("metadata", {}) if vector_result else {}
                if not metadata and bm25_result:
                    metadata = bm25_result.get("metadata", {})  # type: ignore[union-attr]

                combined_results.append(
                    {
                        "id": doc_id,
                        "content": vector_result.get("content")
                        if vector_result
                        else (bm25_result.get("content", "") if bm25_result else ""),
                        "metadata": metadata,
                        "vector_similarity": vector_sim,
                        "bm25_score": bm25_result.get("bm25_score", 0.0) if bm25_result else 0.0,
                        "normalized_bm25": bm25_norm,
                        "combined_score": combined_score,
                    }
                )

        # 結合スコア降順でソート
        combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return combined_results[:top_k]

    def rebuild_bm25_index(self, collection_name: str):
        """コレクション全体からBM25インデックスを再構築する"""
        if not HAS_BM25:
            logger.warning("[VECTOR STORE] BM25 not available, skipping rebuild")
            return

        collection = self.get_collection(collection_name)
        if not collection:
            logger.warning(
                f"[VECTOR STORE] Collection '{collection_name}' not found for BM25 rebuild"
            )
            return

        try:
            # 全ドキュメントを取得
            results = collection.get(include=["documents", "metadatas"])
            if not results["ids"] or len(results["ids"]) == 0:
                logger.info(
                    f"[VECTOR STORE] Collection '{collection_name}' is empty, skipping BM25 rebuild"
                )
                return

            documents = results["documents"]
            doc_ids = results["ids"]

            self._build_bm25_index(collection_name, documents, doc_ids)
            logger.info(
                f"[VECTOR STORE] Rebuilt BM25 index for '{collection_name}' with {len(documents)} documents"
            )
        except Exception as e:
            logger.error(
                f"[VECTOR STORE] Failed to rebuild BM25 index for '{collection_name}': {e}"
            )

    async def rebuild_bm25_index_async(self, collection_name: str) -> None:
        """``rebuild_bm25_index`` の非同期版. 内部で ``asyncio.to_thread`` を使用."""
        import asyncio

        await asyncio.to_thread(self.rebuild_bm25_index, collection_name)


class PgVectorStore(BaseVectorStore):
    """
    PostgreSQL + pgvector を使用したベクトルデータベース管理クラス。
    HNSW/IVFFlat インデックスを使用した高速類似度検索を提供する。
    """

    def __init__(
        self,
        database_url: str,
        *,
        dimension: int = 1536,
        pool_size: int = 10,
        max_overflow: int = 20,
    ) -> None:
        if not HAS_PGVECTOR:
            raise RuntimeError("pgvector is not installed. Install with: pip install pgvector")

        self.database_url = database_url
        self.dimension = dimension
        self._engine = create_async_engine(
            database_url.replace("postgresql://", "postgresql+asyncpg://"),
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._initialized_tables: set[str] = set()

    async def _get_session(self) -> AsyncSession:
        """Create a new session. Use as: async with self._session() as session:"""
        return self._session_factory()

    async def _session(self):
        """Context manager for session. Use as: async with self._session() as session:"""
        async with self._session_factory() as session:
            yield session

    def _get_table_name(self, collection_name: str) -> str:
        """コレクション名からテーブル名を生成（サニタイズ）."""
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", collection_name)
        return f"vec_{safe_name}"

    async def _ensure_table(self, collection_name: str, space: str = "cosine") -> bool:
        """テーブルとインデックスの存在確認・作成."""
        if collection_name in self._initialized_tables:
            return True

        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                # pgvector拡張の確認
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

                # テーブル作成
                create_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector({self.dimension}),
                        metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """
                await session.execute(text(create_table_sql))

                # HNSWインデックス作成（cosine距離用）
                index_name = f"idx_{table_name}_embedding_hnsw"
                create_index_sql = f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {table_name} USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 100);
                """
                await session.execute(text(create_index_sql))

                # メタデータ用GINインデックス
                metadata_index = f"idx_{table_name}_metadata_gin"
                await session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {metadata_index}
                    ON {table_name} USING gin (metadata);
                """))

                await session.commit()
                self._initialized_tables.add(collection_name)
                logger.info(f"[PGVECTOR STORE] Initialized table '{table_name}' with HNSW index")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to initialize table '{table_name}': {e}")
                return False

    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """ドキュメントをベクトルDBに追加する (バッチINSERT)."""
        if not ids:
            return

        await self._ensure_table(collection_name)
        table_name = self._get_table_name(collection_name)

        # バッチサイズ制限（PostgreSQLのパラメータ制限考慮）
        batch_size = 100
        total = len(ids)

        async with self._session() as session:
            try:
                for start in range(0, total, batch_size):
                    end = min(start + batch_size, total)
                    batch_ids = ids[start:end]
                    batch_docs = documents[start:end]
                    batch_embs = embeddings[start:end]
                    batch_metas = metadatas[start:end] if metadatas else [{} for _ in range(end - start)]

                    # UPSERT (ON CONFLICT DO UPDATE)
                    values = []
                    params = {}
                    for i, (doc_id, doc, emb, meta) in enumerate(zip(batch_ids, batch_docs, batch_embs, batch_metas)):
                        param_prefix = f"doc{start + i}"
                        values.append(
                            f"(:{param_prefix}_id, :{param_prefix}_content, :{param_prefix}_emb, :{param_prefix}_meta)"
                        )
                        params[f"{param_prefix}_id"] = doc_id
                        params[f"{param_prefix}_content"] = doc
                        params[f"{param_prefix}_emb"] = emb  # type: ignore[assignment]
                        params[f"{param_prefix}_meta"] = json.dumps(meta, ensure_ascii=False)

                    values_sql = ", ".join(values)
                    upsert_sql = f"""
                        INSERT INTO {table_name} (id, content, embedding, metadata)
                        VALUES {values_sql}
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata;
                    """
                    await session.execute(text(upsert_sql), params)

                await session.commit()
                logger.info(f"[PGVECTOR STORE] Added {total} documents to table '{table_name}'")
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to add documents to '{table_name}': {e}")
                raise

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """ベクトル類似度検索を実行する (コサイン距離)."""
        table_name = self._get_table_name(collection_name)
        await self._ensure_table(collection_name)

        async with self._session() as session:
            try:
                # WHERE句の構築（メタデータフィルタ）
                where_clause = ""
                params: dict[str, Any] = {"query_emb": query_embedding, "limit": top_k}

                if where:
                    conditions = []
                    for i, (key, value) in enumerate(where.items()):
                        param_key = f"meta_{i}"
                        conditions.append(f"metadata->>'{key}' = :{param_key}")
                        params[param_key] = str(value)
                    where_clause = "WHERE " + " AND ".join(conditions)

                search_sql = f"""
                    SELECT id, content, metadata, embedding <=> :query_emb AS distance
                    FROM {table_name}
                    {where_clause}
                    ORDER BY embedding <=> :query_emb
                    LIMIT :limit;
                """

                result = await session.execute(text(search_sql), params)
                rows = result.fetchall()

                output = []
                for row in rows:
                    distance = float(row.distance) if row.distance is not None else 1.0
                    similarity = 1.0 - distance
                    output.append({
                        "id": row.id,
                        "content": row.content,
                        "metadata": row.metadata if isinstance(row.metadata, dict) else {},
                        "distance": distance,
                        "similarity": similarity,
                    })
                return output
            except Exception as e:
                logger.error(f"[PGVECTOR STORE] Search failed for '{table_name}': {e}")
                return []

    async def search_with_score(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """スコア閾値付き検索（コサイン類似度ベース）."""
        results = await self.search(collection_name, query_embedding, top_k, where)

        filtered = []
        for r in results:
            similarity = r.get("similarity", 0.0)
            if similarity >= min_score:
                r["similarity"] = similarity
                filtered.append(r)

        filtered.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return filtered

    async def delete_by_id(self, collection_name: str, ids: list[str]) -> None:
        """指定したIDのドキュメントを削除する."""
        if not ids:
            return

        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                # バッチ削除
                placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
                params = {f"id_{i}": id_val for i, id_val in enumerate(ids)}
                delete_sql = f"DELETE FROM {table_name} WHERE id IN ({placeholders});"
                await session.execute(text(delete_sql), params)
                await session.commit()
                logger.info(f"[PGVECTOR STORE] Deleted {len(ids)} documents from '{table_name}'")
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to delete from '{table_name}': {e}")
                raise

    async def clear_collection(self, collection_name: str) -> None:
        """コレクション（テーブル）を空にする."""
        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                await session.execute(text(f"TRUNCATE TABLE {table_name};"))
                await session.commit()
                logger.info(f"[PGVECTOR STORE] Cleared table '{table_name}'")
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to clear '{table_name}': {e}")
                raise

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """コレクションの統計情報を取得."""
        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                count = result.scalar() or 0
                return {"count": count, "name": collection_name, "table": table_name}
            except Exception as e:
                logger.error(f"[PGVECTOR STORE] Failed to get stats for '{table_name}': {e}")
                return {"count": 0, "error": str(e)}

    async def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        alpha: float = 0.5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        ハイブリッド検索: ベクトル類似度検索 + 全文検索 (tsvector)

        PostgreSQLのtsvectorを使用したキーワード検索とベクトル検索を統合。
        """
        if alpha < 0.0 or alpha > 1.0:
            logger.warning(f"[PGVECTOR STORE] hybrid_search alpha={alpha} out of [0,1], clamping.")
            alpha = max(0.0, min(1.0, alpha))

        table_name = self._get_table_name(collection_name)
        await self._ensure_table(collection_name)

        # ベクトル検索（より多く取得して後でフィルタリング）
        vector_results = await self.search_with_score(
            collection_name, query_embedding, top_k * 3, where, min_score=0.0
        )

        # 全文検索 (tsvector)
        text_results = []
        async with self._session() as session:
            try:
                # tsvector検索用クエリ
                # plainto_tsqueryでクエリをパース
                where_clause = ""
                params = {"query_text": query_text, "limit": top_k * 3}

                if where:
                    conditions = []
                    for i, (key, value) in enumerate(where.items()):
                        param_key = f"meta_{i}"
                        conditions.append(f"metadata->>'{key}' = :{param_key}")
                        params[param_key] = str(value)
                    where_clause = "AND " + " AND ".join(conditions)

                text_search_sql = f"""
                    SELECT id, content, metadata,
                           ts_rank_cd(to_tsvector('simple', content), plainto_tsquery('simple', :query_text)) AS rank
                    FROM {table_name}
                    WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', :query_text)
                    {where_clause}
                    ORDER BY rank DESC
                    LIMIT :limit;
                """

                result = await session.execute(text(text_search_sql), params)
                rows = result.fetchall()

                for row in rows:
                    text_results.append({
                        "id": row.id,
                        "content": row.content,
                        "metadata": row.metadata if isinstance(row.metadata, dict) else {},
                        "rank": float(row.rank) if row.rank else 0.0,
                    })
            except Exception as e:
                logger.debug(f"[PGVECTOR STORE] Full-text search failed: {e}")

        # 結果を結合（RRF - Reciprocal Rank Fusion）
        return self._fuse_results(vector_results, text_results, top_k, alpha, min_score)

    def _fuse_results(
        self,
        vector_results: list[dict[str, Any]],
        text_results: list[dict[str, Any]],
        top_k: int,
        alpha: float,
        min_score: float,
    ) -> list[dict[str, Any]]:
        """ベクトル検索と全文検索の結果をRRFで融合."""
        # IDでマップ化
        vector_map = {r["id"]: r for r in vector_results}
        text_map = {r["id"]: r for r in text_results}
        all_ids = set(vector_map.keys()) | set(text_map.keys())

        # ランキング計算
        vector_rank = {r["id"]: i + 1 for i, r in enumerate(vector_results)}
        text_rank = {r["id"]: i + 1 for i, r in enumerate(text_results)}

        combined = []
        k = 60  # RRF定数

        for doc_id in all_ids:
            v_result = vector_map.get(doc_id)
            t_result = text_map.get(doc_id)

            # RRFスコア計算
            v_rank = vector_rank.get(doc_id, len(vector_results) + 1)
            t_rank = text_rank.get(doc_id, len(text_results) + 1)

            rrf_score = (alpha / (k + v_rank)) + ((1 - alpha) / (k + t_rank))

            if rrf_score >= min_score:
                # ベクトル検索のメタデータを優先
                metadata = v_result.get("metadata", {}) if v_result else {}
                if not metadata and t_result:
                    metadata = t_result.get("metadata", {})

                combined.append({
                    "id": doc_id,
                    "content": v_result.get("content") if v_result else (t_result.get("content", "") if t_result else ""),
                    "metadata": metadata,
                    "vector_similarity": v_result.get("similarity", 0.0) if v_result else 0.0,
                    "text_rank": t_result.get("rank", 0.0) if t_result else 0.0,
                    "rrf_score": rrf_score,
                })

        combined.sort(key=lambda x: x["rrf_score"], reverse=True)
        return combined[:top_k]

    async def close(self) -> None:
        """エンジンを閉じる."""
        await self._engine.dispose()
        logger.info("[PGVECTOR STORE] Engine disposed")


class InMemoryFallbackStore(BaseVectorStore):
    """Pure-Python in-memory vector store. Used when chromadb is unavailable.

    Suitable for small corpora (≤ a few thousand documents) and tests.
    Each collection maintains a FIFO ring buffer capped at ``max_items_per_collection``.
    """

    def __init__(self, max_items_per_collection: int = 10000) -> None:
        self._max = max(1, int(max_items_per_collection))
        self._data: dict[str, list[tuple[str, str, list[float], dict[str, Any]]]] = {}

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if not na or not nb:
            return 0.0
        return dot / (na * nb)

    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        if not ids:
            return
        bucket = self._data.setdefault(collection_name, [])
        for i, (doc_id, doc, emb) in enumerate(zip(ids, documents, embeddings)):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            bucket.append((doc_id, doc, list(emb), dict(meta)))
        # Trim from head (FIFO).
        if len(bucket) > self._max:
            del bucket[: len(bucket) - self._max]

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        bucket = self._data.get(collection_name, [])
        scored: list[tuple[float, str, str, dict[str, Any]]] = []
        for doc_id, doc, emb, meta in bucket:
            if where and not _metadata_matches(meta, where):
                continue
            sim = self._cosine(query_embedding, emb)
            scored.append((sim, doc_id, doc, meta))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for sim, doc_id, doc, meta in scored[: max(0, top_k)]:
            out.append(
                {
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": 1.0 - sim,
                    "similarity": sim,
                }
            )
        return out

    async def delete_by_id(self, collection_name: str, ids: list[str]) -> None:
        bucket = self._data.get(collection_name)
        if not bucket:
            return
        target = set(ids)
        self._data[collection_name] = [
            (i, d, e, m) for (i, d, e, m) in bucket if i not in target
        ]

    async def clear_collection(self, collection_name: str) -> None:
        self._data.pop(collection_name, None)

    async def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        alpha: float = 0.5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Hybrid search that gracefully degrades to vector-only.

        BM25 is not supported in the in-memory store; we just return vector results
        with ``combined_score = vector_similarity`` for API compatibility.
        """
        results = await self.search(
            collection_name, query_embedding, top_k=top_k, where=where
        )
        for r in results:
            sim = r.get("similarity", 0.0)
            r["vector_similarity"] = sim
            r["bm25_score"] = 0.0
            r["normalized_bm25"] = 0.0
            r["combined_score"] = sim
        return [r for r in results if r["combined_score"] >= min_score]


def _metadata_matches(meta: dict[str, Any], where: dict[str, Any]) -> bool:
    for k, v in (where or {}).items():
        if meta.get(k) != v:
            return False
    return True


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

    # pgvector優先
    if mode == "pgvector" or (mode == "auto" and HAS_PGVECTOR):
        if not HAS_PGVECTOR:
            if mode == "pgvector":
                raise RuntimeError("AUTONOVEL_RAG_MODE=pgvector but pgvector is not installed")
        else:
            database_url = settings.DATABASE_URL
            if database_url.startswith("sqlite"):
                logger.warning("[VECTOR STORE] pgvector requires PostgreSQL, falling back to chroma/memory")
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
        return InMemoryFallbackStore(max_items_per_collection=max_items_per_collection)

    # auto fallback
    return InMemoryFallbackStore(max_items_per_collection=max_items_per_collection)


__all__ = [
    "BaseVectorStore",
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
]
