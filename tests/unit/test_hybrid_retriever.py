"""Unit tests for RRF fusion and HybridRetriever (Part 2 / Steps 19-24)."""

import pytest
from unittest.mock import MagicMock

from src.services.rrf_fusion import compute_rrf_scores, FusionResult
from src.services.sparse_retriever import BM25SparseRetriever
from src.services.hybrid_retriever import HybridRetriever
from src.services.rag_service import SearchResult
from src.services.reflective_rag import ReflectiveRAGService


def test_compute_rrf_scores():
    """Test RRF reciprocal ranking and score calculations (Step 19)."""
    dense_results = [
        SearchResult(id="doc1", content="Text 1", metadata={}, source="dense", score=0.9),
        SearchResult(id="doc2", content="Text 2", metadata={}, source="dense", score=0.8),
        SearchResult(id="doc3", content="Text 3", metadata={}, source="dense", score=0.7),
    ]
    sparse_results = [
        SearchResult(id="doc2", content="Text 2", metadata={}, source="sparse", score=10.5),
        SearchResult(id="doc1", content="Text 1", metadata={}, source="sparse", score=8.2),
        SearchResult(id="doc4", content="Text 4", metadata={}, source="sparse", score=5.1),
    ]

    fused = compute_rrf_scores(dense_results, sparse_results, k=60)
    assert len(fused) == 4

    # doc1 and doc2 appear in both and should rank at the top
    top_ids = [f.doc_id for f in fused[:2]]
    assert "doc1" in top_ids
    assert "doc2" in top_ids

    # Check that scores are strictly descending
    scores = [f.score for f in fused]
    assert scores == sorted(scores, reverse=True)


def test_bm25_sparse_retriever():
    """Test BM25SparseRetriever indexing and searching (Step 20)."""
    retriever = BM25SparseRetriever()
    corpus = [
        {"id": "doc1", "content": "勇者は古代の聖剣を手に入れた。"},
        {"id": "doc2", "content": "魔法使いは失われた禁術の書を解読した。"},
        {"id": "doc3", "content": "暗殺者は夜の闇に紛れて王宮へ潜入した。"},
    ]
    retriever.index_documents(corpus)

    results = retriever.search("古代の聖剣", top_k=2)
    assert len(results) > 0
    assert results[0].id == "doc1"
    assert "聖剣" in results[0].content


def test_hybrid_retriever_fusion_and_deduplication():
    """Test HybridRetriever combines dense and sparse sources (Steps 21 & 23)."""
    mock_dense = MagicMock()
    mock_dense.search.return_value = [
        SearchResult(id="doc_a", content="Dense result A", metadata={"tag": "a"}, source="dense", score=0.9),
        SearchResult(id="doc_b", content="Dense result B", metadata={"tag": "b"}, source="dense", score=0.7),
    ]

    sparse_retriever = BM25SparseRetriever()
    sparse_retriever.documents = [
        {"id": "doc_b", "content": "Dense result B", "metadata": {"tag": "b"}},
        {"id": "doc_c", "content": "Sparse result C", "metadata": {"tag": "c"}},
    ]
    # Simulate search result
    sparse_retriever.search = MagicMock(return_value=[
        SearchResult(id="doc_b", content="Dense result B", metadata={"tag": "b"}, source="bm25", score=5.0),
        SearchResult(id="doc_c", content="Sparse result C", metadata={"tag": "c"}, source="bm25", score=3.0),
    ])

    hybrid = HybridRetriever(dense_retriever=mock_dense, sparse_retriever=sparse_retriever)
    fused_results = hybrid.search("any query", top_k=3)

    assert len(fused_results) == 3
    # doc_b appears in both, so it should rank first with normalized score 1.0
    assert fused_results[0].id == "doc_b"
    assert fused_results[0].score == 1.0
    assert fused_results[0].source == "hybrid_rrf"


@pytest.mark.asyncio
async def test_reflective_rag_with_hybrid_retriever():
    """Test ReflectiveRAGService integrated with HybridRetriever (Step 22)."""
    mock_rag = MagicMock()
    mock_hybrid = MagicMock()
    mock_hybrid.search.return_value = [
        SearchResult(id="h1", content="ハイブリッド検索による重要設定", metadata={}, source="hybrid_rrf", score=0.95),
    ]

    service = ReflectiveRAGService(
        rag_service=mock_rag,
        hybrid_retriever=mock_hybrid,
        max_iter=1,
    )

    mock_session = MagicMock()
    result = await service.retrieve_with_reflection(mock_session, query="重要設定")

    mock_hybrid.search.assert_called_once()
    assert len(result.documents) == 1
    assert result.documents[0].search_result.id == "h1"
