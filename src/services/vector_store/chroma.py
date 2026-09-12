"""
src/services/vector_store/chroma.py - ChromaDB ベクトルストア実装
"""
from __future__ import annotations

import logging
import re
from typing import Any, TYPE_CHECKING

from src.services.vector_store.base import (
    BaseVectorStore,
    CollectionType,
    CollectionConfig,
    DEFAULT_COLLECTIONS,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import chromadb
    from chromadb.api import ClientAPI
else:
    ClientAPI = Any

try:
    import chromadb
    HAS_CHROMA = True
except Exception as e:
    logger.warning(f"[VECTOR STORE] Failed to import/initialize chromadb: {e}.")
    HAS_CHROMA = False

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except Exception:
    HAS_BM25 = False

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
        return [items[i : i + size] for i in range(0, len(items), size)]

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
            logger.debug(f"[VECTOR STORE] collection.count() failed, falling back to peek: {e}")
            try:
                peeked = collection.peek(limit=1)
                exists = bool(peeked and peeked.get("ids"))
                return {"count": -1 if not exists else 1, "name": collection_name}
            except Exception as e2:
                logger.error(f"[VECTOR STORE] Failed to get stats for '{collection_name}': {e2}")
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

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """ドキュメントをトークン化（簡易的な日本語対応：文字単位 + スペース区切り）"""
        # 英数字の単語 + 日本語文字（ひらがな、カタカナ、漢字）
        tokens = re.findall(
            r"[a-zA-Z0-9]+|[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", text.lower()
        )
        # さらに文字単位でも分割（日本語の部分一致対応）
        char_tokens = list(text.lower())
        return tokens + char_tokens

    def _build_bm25_index(self, collection_name: str, documents: list[str], doc_ids: list[str]):
        """BM25インデックスを構築または更新する"""
        if not HAS_BM25:
            logger.warning("[VECTOR STORE] BM25 not available, skipping index build")
            return

        corpus_tokens = [self._tokenize(doc) for doc in documents]
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
            logger.warning(f"[VECTOR STORE] hybrid_search alpha={alpha} out of [0,1], clamping.")
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

            query_tokens = self._tokenize(query_text)
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




__all__ = ["ChromaClientProvider", "ChromaVectorStore", "HAS_CHROMA", "HAS_BM25"]
