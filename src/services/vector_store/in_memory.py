"""
src/services/vector_store/in_memory.py - Pure-Python インメモリベクトルストア
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    HAS_NETWORKX = True
except Exception as e:
    logger.warning(f"[VECTOR STORE] networkx not available: {e}")
    HAS_NETWORKX = False

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except Exception as e:
    logger.warning(f"[VECTOR STORE] rank_bm25 not available: {e}")
    HAS_BM25 = False


def _metadata_matches(meta: dict[str, Any], where: dict[str, Any]) -> bool:
    for k, v in (where or {}).items():
        if meta.get(k) != v:
            return False
    return True


class InMemoryFallbackStore(BaseVectorStore):
    """Pure-Python in-memory vector store. Used when chromadb is unavailable.

    Suitable for small corpora (≤ a few thousand documents) and tests.
    Each collection maintains a FIFO ring buffer capped at ``max_items_per_collection``.
    """

    def __init__(self, max_items_per_collection: int = 10000, enable_graph: bool = True) -> None:
        self._max = max(1, int(max_items_per_collection))
        self._data: dict[str, list[tuple[str, str, list[float], dict[str, Any]]]] = {}
        # BM25 インデックス: collection_name -> {"bm25": BM25Okapi, "corpus_tokens": List[List[str]], "doc_ids": List[str]}
        self._bm25_indexes: dict[str, dict[str, Any]] = {}
        # グラフ層（NetworkX）
        self._graphs: dict[str, nx.MultiDiGraph] = {}
        self._enable_graph = enable_graph and HAS_NETWORKX

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

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """ChromaVectorStore._tokenize と同等の簡易トークナイズ（日本語文字 + 英数字）"""
        import re
        tokens = re.findall(r"[a-zA-Z0-9]+|[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", text.lower())
        char_tokens = list(text.lower())
        return tokens + char_tokens

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

        # BM25 インデックス更新
        if HAS_BM25:
            documents = [doc for _, doc, _, _ in bucket]
            doc_ids = [doc_id for doc_id, _, _, _ in bucket]
            corpus_tokens = [self._tokenize(doc) for doc in documents]
            self._bm25_indexes[collection_name] = {
                "bm25": BM25Okapi(corpus_tokens),
                "corpus_tokens": corpus_tokens,
                "doc_ids": doc_ids,
            }

        # グラフ更新（メタデータに entities / relations があればエッジ登録）
        if self._enable_graph:
            g = self._graphs.setdefault(collection_name, nx.MultiDiGraph())
            bucket = self._data[collection_name]
            for _, _, _, meta in bucket:
                entities = meta.get("entities") or []
                if isinstance(entities, list):
                    for ent in entities:
                        g.add_node(ent, **meta)
                relations = meta.get("relations") or []
                if isinstance(relations, list):
                    for rel in relations:
                        if isinstance(rel, dict) and "src" in rel and "dst" in rel:
                            g.add_edge(rel["src"], rel["dst"], rel_type=rel.get("type", "related"), **meta)

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
        # メインデータから削除
        self._data[collection_name] = [(i, d, e, m) for (i, d, e, m) in bucket if i not in target]

        # BM25 インデックス再構築
        if HAS_BM25 and collection_name in self._bm25_indexes:
            new_bucket = self._data[collection_name]
            documents = [doc for _, doc, _, _ in new_bucket]
            doc_ids = [doc_id for doc_id, _, _, _ in new_bucket]
            if documents:
                corpus_tokens = [self._tokenize(doc) for doc in documents]
                self._bm25_indexes[collection_name] = {
                    "bm25": BM25Okapi(corpus_tokens),
                    "corpus_tokens": corpus_tokens,
                    "doc_ids": doc_ids,
                }
            else:
                del self._bm25_indexes[collection_name]

        # グラフからノード削除（関連エッジも自動削除）
        if self._enable_graph and collection_name in self._graphs:
            g = self._graphs[collection_name]
            for node_id in target:
                if node_id in g:
                    g.remove_node(node_id)

    async def clear_collection(self, collection_name: str) -> None:
        self._data.pop(collection_name, None)
        self._bm25_indexes.pop(collection_name, None)
        if self._enable_graph:
            self._graphs.pop(collection_name, None)

    async def search_with_score(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        bucket = self._data.get(collection_name, [])
        scored: list[tuple[float, str, str, dict[str, Any]]] = []
        for doc_id, doc, emb, meta in bucket:
            if where and not _metadata_matches(meta, where):
                continue
            sim = self._cosine(query_embedding, emb)
            if sim < min_score:
                continue
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
        """Dense ベクトル検索 + BM25 Sparse 検索を RRF で融合"""
        if alpha < 0.0 or alpha > 1.0:
            logger.warning(f"[VECTOR STORE] hybrid_search alpha={alpha} out of [0,1], clamping.")
            alpha = max(0.0, min(1.0, alpha))

        # 1) ベクトル検索（多めに取得）
        vector_results = await self.search(collection_name, query_embedding, top_k * 3, where)

        # 2) BM25 検索
        bm25_results = []
        if HAS_BM25 and collection_name in self._bm25_indexes:
            bm25_data = self._bm25_indexes[collection_name]
            bm25 = bm25_data["bm25"]
            doc_ids = bm25_data["doc_ids"]
            # メタデータフィルタ適用のため元 bucket 参照
            bucket = self._data.get(collection_name, [])
            id_to_doc = {doc_id: (doc, meta) for doc_id, doc, _, meta in bucket}

            query_tokens = self._tokenize(query_text)
            bm25_scores = bm25.get_scores(query_tokens)

            top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[: top_k * 3]
            if len(bm25_scores) > 0:
                max_bm25 = max(bm25_scores)
                min_bm25 = min(bm25_scores)
            else:
                max_bm25 = 1.0
                min_bm25 = 0.0
            bm25_range = max_bm25 - min_bm25 if max_bm25 > min_bm25 else 1.0

            for idx in top_indices:
                if bm25_scores[idx] <= 0:
                    continue
                doc_id = doc_ids[idx]
                if where and not _metadata_matches(id_to_doc.get(doc_id, (None, {}))[1], where):
                    continue
                normalized_bm25 = (bm25_scores[idx] - min_bm25) / bm25_range
                doc_content, meta = id_to_doc.get(doc_id, ("", {}))
                bm25_results.append({
                    "id": doc_id,
                    "content": doc_content,
                    "bm25_score": bm25_scores[idx],
                    "normalized_bm25": normalized_bm25,
                    "metadata": meta,
                })

        # 3) RRF 融合（k=60）
        vector_map = {r["id"]: r for r in vector_results}
        bm25_map = {r["id"]: r for r in bm25_results}
        all_ids = set(vector_map.keys()) | set(bm25_map.keys())

        vector_rank = {r["id"]: i + 1 for i, r in enumerate(vector_results)}
        bm25_rank = {r["id"]: i + 1 for i, r in enumerate(bm25_results)}
        k = 60

        combined = []
        for doc_id in all_ids:
            v = vector_map.get(doc_id)
            b = bm25_map.get(doc_id)
            v_rank = vector_rank.get(doc_id, len(vector_results) + 1)
            b_rank = bm25_rank.get(doc_id, len(bm25_results) + 1)
            rrf = (alpha / (k + v_rank)) + ((1 - alpha) / (k + b_rank))
            if rrf >= min_score:
                metadata = v.get("metadata", {}) if v else (b.get("metadata", {}) if b else {})
                combined.append({
                    "id": doc_id,
                    "content": v.get("content") if v else (b.get("content", "") if b else ""),
                    "metadata": metadata,
                    "vector_similarity": v.get("similarity", 0.0) if v else 0.0,
                    "bm25_score": b.get("bm25_score", 0.0) if b else 0.0,
                    "normalized_bm25": b.get("normalized_bm25", 0.0) if b else 0.0,
                    "combined_score": rrf,
                })

        combined.sort(key=lambda x: x["combined_score"], reverse=True)
        return combined[:top_k]

    async def get_neighbors(
        self,
        collection_name: str,
        entity: str,
        *,
        rel_type: str | None = None,
        max_depth: int = 1,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """指定エンティティの近傍ノードを取得（BFS）"""
        if not self._enable_graph:
            return []
        g = self._graphs.get(collection_name)
        if not g or entity not in g:
            return []

        visited = set([entity])
        frontier = [(entity, 0)]
        results = []

        while frontier and len(results) < limit:
            node, depth = frontier.pop(0)
            if depth >= max_depth:
                continue
            for _, nbr, data in g.out_edges(node, data=True):
                if rel_type and data.get("rel_type") != rel_type:
                    continue
                if nbr not in visited:
                    visited.add(nbr)
                    results.append({
                        "entity": nbr,
                        "relation": data.get("rel_type", "related"),
                        "depth": depth + 1,
                        "metadata": {k: v for k, v in data.items() if k != "rel_type"},
                    })
                    frontier.append((nbr, depth + 1))
            for nbr, _, data in g.in_edges(node, data=True):
                if rel_type and data.get("rel_type") != rel_type:
                    continue
                if nbr not in visited:
                    visited.add(nbr)
                    results.append({
                        "entity": nbr,
                        "relation": f"reverse_{data.get('rel_type', 'related')}",
                        "depth": depth + 1,
                        "metadata": {k: v for k, v in data.items() if k != "rel_type"},
                    })
                    frontier.append((nbr, depth + 1))
        return results[:limit]

    async def check_entity_validity(
        self,
        collection_name: str,
        entity_name: str,
    ) -> dict[str, Any]:
        """ReflectiveRAGService._context_fit_check から呼ばれる想定の互換インターフェース"""
        if not self._enable_graph:
            return {"valid": True, "is_forbidden": False, "is_retired": False, "status": "active"}
        g = self._graphs.get(collection_name)
        if not g or entity_name not in g:
            return {"valid": True, "is_forbidden": False, "is_retired": False, "status": "active"}

        node_data = g.nodes[entity_name]
        status = node_data.get("status", "active")
        is_forbidden = status in ("forbidden", "banned", "deprecated")
        is_retired = status in ("dead", "destroyed", "sealed", "retired")
        valid = not is_forbidden and not is_retired

        return {
            "valid": valid,
            "is_forbidden": is_forbidden,
            "is_retired": is_retired,
            "status": status,
            "entity_name": entity_name,
        }


__all__ = ["InMemoryFallbackStore", "_metadata_matches"]
