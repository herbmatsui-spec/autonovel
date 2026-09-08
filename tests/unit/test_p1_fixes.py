"""Unit tests for P1 fixes: RateLimiter, GraphRAGService cache, PgVectorStore validation."""

import time
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from src.backend.rate_limit import RateLimiter
from src.services.rag_service import GraphRAGService, RagContext
from src.services.vector_store import PgVectorStore


def test_rate_limiter_prunes_inactive_clients():
    limiter = RateLimiter(max_requests=2, window_seconds=1)
    req1 = MagicMock()
    req1.client.host = "1.1.1.1"
    req2 = MagicMock()
    req2.client.host = "2.2.2.2"

    limiter.check(req1)
    assert "1.1.1.1" in limiter._requests

    # Wait for window to expire
    time.sleep(1.05)

    # Force check counter to trigger periodic pruning
    limiter._check_counter = 99
    limiter.check(req2)
    assert "2.2.2.2" in limiter._requests
    # Inactive 1.1.1.1 should have been pruned
    assert "1.1.1.1" not in limiter._requests


def test_graph_rag_service_cache_bounded():
    rag = GraphRAGService(enable_cache=True)
    rag._max_cache_size = 3
    rag._cache_ttl = 60

    dummy_ctx = RagContext(
        graph_context="",
        vector_context="",
        fulltext_context="",
        stats={},
        token_estimate=10,
    )

    rag._set_cache("k1", dummy_ctx)
    rag._set_cache("k2", dummy_ctx)
    rag._set_cache("k3", dummy_ctx)
    assert len(rag._cache) == 3

    # Adding 4th should prune oldest
    rag._set_cache("k4", dummy_ctx)
    assert len(rag._cache) <= 3
    assert "k4" in rag._cache
    assert "k1" not in rag._cache


def test_pgvector_metadata_key_validation():
    # Valid keys
    assert PgVectorStore._validate_metadata_key("author") == "author"
    assert PgVectorStore._validate_metadata_key("chapter_123") == "chapter_123"

    # Malicious keys with SQL injection attempts
    with pytest.raises(ValueError):
        PgVectorStore._validate_metadata_key("author' OR '1'='1")

    with pytest.raises(ValueError):
        PgVectorStore._validate_metadata_key("key; DROP TABLE users;--")
