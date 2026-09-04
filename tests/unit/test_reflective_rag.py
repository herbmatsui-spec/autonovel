"""Unit tests for ReflectiveRAGService."""

import pytest
import asyncio
from unittest.mock import MagicMock

from src.services.reflective_rag import ReflectiveRAGService, ReflectiveRetrievalResult
from src.services.rag_service import GraphRAGService, SearchResult
from sqlalchemy.orm import Session


@pytest.fixture
def mock_rag_service():
    rag = MagicMock(spec=GraphRAGService)
    return rag


@pytest.fixture
def sample_docs():
    return [
        SearchResult(id="1", content="アリスは東京で剣を振った", metadata={}, source="vector", score=0.9),
        SearchResult(id="2", content="ボブは大阪で杖を使った", metadata={}, source="vector", score=0.8),
        SearchResult(id="3", content="カロルは京都で弓を引いた", metadata={}, source="vector", score=0.7),
    ]


class TestReflectiveRAGService:
    def test_bm25_keyword_extract(self, mock_rag_service, sample_docs):
        reflective = ReflectiveRAGService(rag_service=mock_rag_service)
        keywords = reflective._bm25_keyword_extract(sample_docs, n=3)
        assert isinstance(keywords, list)
        assert len(keywords) <= 3

    def test_context_fit_check_forbidden(self, mock_rag_service):
        reflective = ReflectiveRAGService(rag_service=mock_rag_service)
        session = MagicMock()
        doc = SearchResult(id="1", content="test", metadata={"is_forbidden": True}, source="vector", score=0.9)
        score = reflective._context_fit_check(session, doc)
        assert score == 0.0

    def test_context_fit_check_normal(self, mock_rag_service):
        reflective = ReflectiveRAGService(rag_service=mock_rag_service)
        session = MagicMock()
        doc = SearchResult(id="1", content="test", metadata={}, source="vector", score=0.9)
        score = reflective._context_fit_check(session, doc)
        assert score == 1.0


class TestRetrieveWithReflection:
    @pytest.mark.asyncio
    async def test_single_iteration_converged(self, mock_rag_service, sample_docs):
        mock_rag_service.search_similar_chunks.return_value = sample_docs
        reflective = ReflectiveRAGService(
            rag_service=mock_rag_service,
            top_k=2,
            max_iter=3,
            relevance_threshold=0.5,
            initial_fetch_k=5,
        )
        session = MagicMock()

        result = await reflective.retrieve_with_reflection(
            session, query="アリス 剣", book_id=1
        )

        assert isinstance(result, ReflectiveRetrievalResult)
        assert result.iterations == 1
        assert result.converged is True
        assert result.original_query == "アリス 剣"
        assert len(result.refined_queries) == 1
        assert len(result.documents) == 2
        assert result.initial_doc_count == 3
        assert result.final_doc_count == 2

    @pytest.mark.asyncio
    async def test_multi_iteration_max_reached(self, mock_rag_service, sample_docs):
        mock_rag_service.search_similar_chunks.return_value = sample_docs
        reflective = ReflectiveRAGService(
            rag_service=mock_rag_service,
            top_k=2,
            max_iter=3,
            relevance_threshold=0.95,
            initial_fetch_k=5,
        )
        session = MagicMock()

        result = await reflective.retrieve_with_reflection(
            session, query="アリス", book_id=1
        )

        assert result.iterations == 3
        assert result.converged is False
        assert len(result.refined_queries) >= 2

    @pytest.mark.asyncio
    async def test_threshold_affects_filtering(self, mock_rag_service, sample_docs):
        mock_rag_service.search_similar_chunks.return_value = sample_docs
        reflective_low = ReflectiveRAGService(
            rag_service=mock_rag_service,
            top_k=2,
            max_iter=1,
            relevance_threshold=0.5,
        )
        reflective_high = ReflectiveRAGService(
            rag_service=mock_rag_service,
            top_k=2,
            max_iter=1,
            relevance_threshold=0.95,
        )
        session = MagicMock()

        result_low = await reflective_low.retrieve_with_reflection(session, query="test", book_id=1)
        result_high = await reflective_high.retrieve_with_reflection(session, query="test", book_id=1)

        assert result_low.history[0]["filtered"] >= result_high.history[0]["filtered"]

    @pytest.mark.asyncio
    async def test_empty_initial_results(self, mock_rag_service):
        mock_rag_service.search_similar_chunks.return_value = []
        reflective = ReflectiveRAGService(rag_service=mock_rag_service)
        session = MagicMock()

        result = await reflective.retrieve_with_reflection(session, query="test", book_id=1)

        assert result.iterations == 1
        assert result.final_doc_count == 0
        assert result.initial_doc_count == 0

    @pytest.mark.asyncio
    async def test_history_recorded(self, mock_rag_service, sample_docs):
        mock_rag_service.search_similar_chunks.return_value = sample_docs
        # Use top_k=2 so 3 docs >= 2 converges on first iteration
        reflective = ReflectiveRAGService(rag_service=mock_rag_service, top_k=2)
        session = MagicMock()

        result = await reflective.retrieve_with_reflection(session, query="test", book_id=1)

        assert len(result.history) == 1
        h = result.history[0]
        assert h["iteration"] == 1
        assert h["query"] == "test"
        assert h["candidates"] == 3
        assert "elapsed_ms" in h