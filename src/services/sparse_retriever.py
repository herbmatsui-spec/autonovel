"""Sparse BM25 Retriever with Japanese morphological tokenization (Step 20).

Indexes novel passages/chunks and executes sparse keyword search using BM25Okapi.
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.nlp.japanese_tokenizer import JapaneseTokenizer
from src.services.rag_service import SearchResult

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

logger = logging.getLogger(__name__)


class BM25SparseRetriever:
    """Sparse retrieval engine powered by SudachiPy morphology and BM25Okapi."""

    def __init__(self, tokenizer: JapaneseTokenizer | None = None) -> None:
        self.tokenizer = tokenizer or JapaneseTokenizer()
        self.documents: list[dict[str, Any]] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    def index_documents(self, documents: list[dict[str, Any]]) -> None:
        """Build BM25 index from a list of document dicts.

        Each doc dict should contain:
            'id': str
            'content': str
            'metadata': dict (optional)
        """
        self.documents = list(documents)
        self._tokenized_corpus = []

        for doc in self.documents:
            text = doc.get("content", "")
            tokens = self.tokenizer.tokenize(text)
            self._tokenized_corpus.append(tokens)

        if BM25Okapi is not None and any(self._tokenized_corpus):
            # Avoid empty lists only
            valid_corpus = [t if t else ["<empty>"] for t in self._tokenized_corpus]
            self._bm25 = BM25Okapi(valid_corpus)
            logger.debug(f"BM25SparseRetriever indexed {len(self.documents)} documents.")
        else:
            self._bm25 = None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search indexed documents using BM25 and return SearchResult list."""
        if not self.documents:
            return []

        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            return []

        if self._bm25 is not None:
            raw_scores = self._bm25.get_scores(query_tokens)
        else:
            # Fallback simple overlap scoring
            q_set = set(query_tokens)
            raw_scores = [
                sum(1 for t in doc_tok if t in q_set)
                for doc_tok in self._tokenized_corpus
            ]

        # Pair scores with documents
        scored_pairs = []
        for idx, score in enumerate(raw_scores):
            if score > 0:
                doc = self.documents[idx]
                scored_pairs.append((float(score), doc))

        # Sort descending
        scored_pairs.sort(key=lambda x: x[0], reverse=True)
        top_pairs = scored_pairs[:top_k]

        results: list[SearchResult] = []
        for score, doc in top_pairs:
            results.append(SearchResult(
                id=str(doc.get("id", "")),
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
                source="bm25_sparse",
                score=score,
            ))
        return results
