"""Unit tests for QueryReformulator and Reflective RAG query rewriting (Part 3 / Steps 25-30)."""

import pytest
from unittest.mock import MagicMock

from src.services.query_reformulator import QueryReformulator
from src.services.reflective_rag import ReflectiveRAGService
from src.services.rag_service import SearchResult


def test_query_reformulator_modes():
    """Test QueryReformulator across various reformulation modes (Steps 25-26)."""
    reformulator = QueryReformulator()
    query = "古代魔法"
    keywords = ["詠唱", "魔力消費", "古代文字"]

    # 1. intent_guided with scene_intent
    rewritten_intent = reformulator.reformulate_query(
        query=query,
        keywords=keywords,
        scene_intent="ダンジョン深部での決戦",
        mode="intent_guided",
    )
    assert "ダンジョン深部での決戦" in rewritten_intent
    assert "古代魔法" in rewritten_intent
    assert "詠唱" in rewritten_intent

    # 2. semantic_expansion
    rewritten_semantic = reformulator.reformulate_query(
        query=query,
        keywords=keywords,
        mode="semantic_expansion",
    )
    assert "古代魔法に関する情報" in rewritten_semantic
    assert "詠唱" in rewritten_semantic

    # 3. empty keywords returns original query
    assert reformulator.reformulate_query(query, []) == query


def test_query_reformulator_hyde_generation():
    """Test hypothetical document passage generation (Step 27)."""
    reformulator = QueryReformulator()
    hyde_chunk = reformulator.generate_hypothetical_chunk(
        query="聖剣エクスカリバーの封印解除条件",
        genre="fantasy",
        keywords=["月蝕", "巫女の祈り"],
    )

    assert "【Fantasy世界観アーカイブ】" in hyde_chunk
    assert "聖剣エクスカリバーの封印解除条件" in hyde_chunk
    assert "月蝕" in hyde_chunk or "巫女の祈り" in hyde_chunk
    assert len(hyde_chunk) > 50


def test_semantic_drift_detection():
    """Test semantic drift monitoring and rejection mechanism (Step 29)."""
    mock_rag = MagicMock()
    service = ReflectiveRAGService(rag_service=mock_rag)

    orig_query = "魔導書と禁呪の解除"

    # Retains keywords (no drift)
    valid_new_query = "魔導書における禁呪の解除方法と必要な儀式"
    assert service._is_semantic_drift(orig_query, valid_new_query, ["儀式"]) is False

    # Completely loses original query keywords (drift detected)
    drifted_query = "現代都市における最新型スポーツカーの馬力と燃費性能"
    assert service._is_semantic_drift(orig_query, drifted_query, ["車", "燃費"]) is True


@pytest.mark.asyncio
async def test_reflective_rag_reformulation_integration():
    """Test ReflectiveRAGService updates queries via QueryReformulator (Step 28)."""
    mock_rag = MagicMock()
    mock_rag.search_similar_chunks.side_effect = [
        # Iteration 1: returns documents with keywords
        [
            SearchResult(id="1", content="古の聖剣には強大な光の加護が宿る", metadata={}, source="dense", score=0.4),
        ],
        # Iteration 2: returns converged document
        [
            SearchResult(id="2", content="聖剣の光の加護を解放する聖なる儀式", metadata={}, source="dense", score=0.9),
        ],
    ]

    reformulator = QueryReformulator()
    service = ReflectiveRAGService(
        rag_service=mock_rag,
        query_reformulator=reformulator,
        max_iter=2,
        relevance_threshold=0.6,
    )

    mock_session = MagicMock()
    res = await service.retrieve_with_reflection(
        mock_session,
        query="聖剣の加護",
        scene_intent="光の神殿での探索",
    )

    # Must have attempted refinement
    assert len(res.refined_queries) >= 1
    # Check that refined query is a natural sentence rather than pure space-separated tokens
    if len(res.refined_queries) > 1:
        assert "における" in res.refined_queries[1] or "に関する" in res.refined_queries[1]
