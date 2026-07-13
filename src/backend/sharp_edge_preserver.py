"""
src/backend/sharp_edge_preserver.py
品質向上（磨き上げ）の前後で「角」が削られていないかを検証するモジュール。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from src.models.sharp_edge import SharpEdgeSpec

logger = logging.getLogger(__name__)

# Attempt to import semantic cache infrastructure
try:
    from src.services.semantic_cache import SemanticCacheManager
    SEMANTIC_CACHE_IMPORTED = True
except ImportError:
    SEMANTIC_CACHE_IMPORTED = False
    logger.warning("SemanticCacheManager not imported - semantic similarity feature disabled")


class SemanticEdgePreserver:
    """
    尖り保全検証器（ストリングマッチ + 意味的類似度）
    1. key_phrase による直接一致チェック（優先）
    2. Semantic similarity（Embedding API が利用可能な場合）
    3. N-gram Jaccard 類似度（フォールバック、低レイテンシ）
    4. フォールバック：description[:20] による文字列チェック
    """

    def __init__(
        self,
        semantic_cache: Optional[SemanticCacheManager] = None,
        similarity_threshold: float = 0.75,
        use_semantic: bool = True,
        use_ngram_fallback: bool = True,
    ):
        self.semantic_cache = semantic_cache
        self.similarity_threshold = similarity_threshold
        self.use_semantic = use_semantic and SEMANTIC_CACHE_IMPORTED
        self.use_ngram_fallback = use_ngram_fallback

    async def check_edges_preserved(
        self,
        before_content: str,
        after_content: str,
        edges: List[SharpEdgeSpec],
    ) -> tuple[List[SharpEdgeSpec], List[SharpEdgeSpec]]:
        """
        角の保全確認を実行。2つの結果を返す：

        - lost_by_string: 文字列チェックで削除された角のリスト
        - lost_by_semantic: 意味的判定で削除された角のリスト

        意味的判定は事前に配置されたセマンティックキャッシュを使用。
        """
        if not edges:
            return [], []

        if not self.use_semantic:
            # Semantic機能が無効な場合は文字列チェックのみ実行
            lost = self._check_string_only(after_content, edges)
            return lost, lost

        # Step 1: String match check (prioritized)
        string_lost = self._check_string_only(after_content, edges)

        # Step 2: Semantic similarity check on string-lost candidates
        semantic_lost = []
        for edge in string_lost:
            similarity = await self._semantic_compare(
                before_content, after_content, edge
            )
            if similarity < self.similarity_threshold:
                semantic_lost.append(edge)
                logger.debug(
                    "意味的類似度で削除検出: %s (similarity=%.2f < %.2f)",
                    edge.edge_type, similarity, self.similarity_threshold
                )
            else:
                logger.debug(
                    "意味的類似度で保持確認: %s (similarity=%.2f >= %.2f)",
                    edge.edge_type, similarity, self.similarity_threshold
                )

        return semantic_lost, string_lost

    def _check_string_only(self, after_content: str, edges: List[SharpEdgeSpec]) -> List[SharpEdgeSpec]:
        """文字列チェック（key_phrase もしくは description[:20]）のみを行う実装"""
        if not edges:
            return []

        lost: List[SharpEdgeSpec] = []
        after_lower = after_content.lower()

        for edge in edges:
            preserved = False

            # Priority 1: key_phrase
            key_phrase = edge.key_phrase.strip() if edge.key_phrase else ""
            if key_phrase:
                if key_phrase.lower() in after_lower:
                    preserved = True
                    logger.debug("key_phraseで保持確認: %s (%s)", edge.edge_type, key_phrase)

            # Priority 2: description[:20] fallback
            if not preserved:
                desc_phrase = edge.description.strip()[:20].lower()
                if desc_phrase and desc_phrase in after_lower:
                    preserved = True
                    logger.debug(
                        "description[:20]で保持確認 (key_phraseなし): %s (%s)", edge.edge_type, desc_phrase
                    )

            if not preserved:
                lost.append(edge)
                logger.debug("角が削除されました: %s", edge.edge_type)

        return lost

    async def _semantic_compare(
        self,
        before_content: str,
        after_content: str,
        edge: SharpEdgeSpec,
    ) -> float:
        """
        key_phrase と after_content の類似度を計算。
        Embedding API が利用可能であれば利用、無理な場合は N-gram 類似度を返す。
        """
        # Use key_phrase or fallback to description[:20] if key_phrase is empty
        key_phrase = edge.key_phrase.strip() or edge.description.strip()[:20]

        if not key_phrase:
            return 0.0

        # Priority 1: embedding-based cosine similarity
        if self.semantic_cache is not None:
            try:
                return await self.semantic_cache.compute_similarity(
                    key_phrase, after_content
                )
            except Exception as e:
                logger.warning(f"Semantic similarity failed: {e}")

        # Priority 2: N-gram Jaccard fallback (embedding-free, low-latency)
        if self.use_ngram_fallback:
            from src.backend.engine_utils import compute_ngram_similarity
            ngram_sim = compute_ngram_similarity(key_phrase, after_content)
            # Treat a decent N-gram overlap as a positive signal
            return ngram_sim

        return 0.0


def check_edges_preserved(before_content: str, after_content: str, edges: List[SharpEdgeSpec]) -> List[SharpEdgeSpec]:
    """
    品質向上前後のコンテンツを比較し、削除された角を検出する（同期版・後方互換）。

    優先順位:
    1. edge.key_phrase (優先) — after_content に key_phrase が字面一致で含まれるか
    2. edge.description[:20] (フォールバック) — description の先頭20字で判定

    削除された edge のリストを返す（空リスト = 全角保持）。
    """
    if not edges:
        return []

    lost: List[SharpEdgeSpec] = []
    after_lower = after_content.lower()

    for edge in edges:
        preserved = False

        # Priority 1: key_phrase (the primary check)
        key_phrase = edge.key_phrase.strip() if edge.key_phrase else ""
        if key_phrase:
            if key_phrase.lower() in after_lower:
                preserved = True
                logger.debug("key_phraseで保持確認: %s (%s)", edge.edge_type, key_phrase)

        # Priority 2: description[:20] fallback (legacy)
        if not preserved:
            desc_phrase = edge.description.strip()[:20].lower()
            if desc_phrase and desc_phrase in after_lower:
                preserved = True
                logger.debug("description[:20]で保持確認 (key_phraseなし): %s (%s)", edge.edge_type, desc_phrase)

        if not preserved:
            lost.append(edge)
            logger.debug("角が削除されました: %s", edge.edge_type)

    return lost
