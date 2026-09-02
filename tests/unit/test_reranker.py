"""Unit tests for Reranker (Noop / Simple / CrossEncoder)."""
from __future__ import annotations

import pytest

from src.services.reranker import (
    HAS_CROSS_ENCODER,
    CrossEncoderReranker,
    NoopReranker,
    SimpleReranker,
    build_default_reranker,
)


class TestNoopReranker:
    @pytest.mark.asyncio
    async def test_preserves_order(self):
        r = NoopReranker()
        out = await r.rerank("q", ["a", "b", "c"], 2)
        assert out == [(0, 0.0), (1, 0.0)]


class TestSimpleReranker:
    @pytest.mark.asyncio
    async def test_orders_by_cosine(self):
        r = SimpleReranker()
        out = await r.rerank("hello world", ["hello world", "totally unrelated"], 2)
        # First doc identical to query → score ~ 1.0
        assert out[0][0] == 0
        assert out[0][1] > out[1][1]


class TestCrossEncoderReranker:
    def test_missing_dep_raises(self):
        if HAS_CROSS_ENCODER:
            pytest.skip("sentence-transformers available in env")
        with pytest.raises(RuntimeError):
            CrossEncoderReranker()


class TestBuildDefault:
    def test_returns_object(self):
        r = build_default_reranker()
        assert r is not None
