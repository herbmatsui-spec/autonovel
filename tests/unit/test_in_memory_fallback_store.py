"""Unit tests for InMemoryFallbackStore."""
from __future__ import annotations

import math

import pytest

from src.services.vector_store import HAS_INMEM, InMemoryFallbackStore


pytestmark = pytest.mark.skipif(
    not HAS_INMEM,
    reason="InMemoryFallbackStore not implemented yet (wip)",
)


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


class TestInMemoryFallbackStore:
    def setup_method(self):
        self.store = InMemoryFallbackStore(max_items_per_collection=10)

    @pytest.mark.asyncio
    async def test_add_and_search(self):
        await self.store.add_documents(
            "c1", ["a", "b"], ["doc a", "doc b"], [[1.0, 0.0], [0.0, 1.0]]
        )
        results = await self.store.search("c1", [1.0, 0.0], top_k=2)
        assert len(results) == 2
        # First result should be 'a' (identical direction)
        assert results[0]["id"] == "a"

    @pytest.mark.asyncio
    async def test_delete_by_id(self):
        await self.store.add_documents(
            "c1", ["a", "b"], ["doc a", "doc b"], [[1.0, 0.0], [0.0, 1.0]]
        )
        await self.store.delete_by_id("c1", ["a"])
        results = await self.store.search("c1", [1.0, 0.0], top_k=5)
        ids = [r["id"] for r in results]
        assert "a" not in ids
        assert "b" in ids

    @pytest.mark.asyncio
    async def test_clear_collection(self):
        await self.store.add_documents("c1", ["a"], ["x"], [[1.0, 0.0]])
        await self.store.clear_collection("c1")
        results = await self.store.search("c1", [1.0, 0.0], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_add_documents_respects_max_items(self):
        small = InMemoryFallbackStore(max_items_per_collection=2)
        await small.add_documents(
            "c1", ["a", "b", "c"], ["a", "b", "c"], [[1.0, 0.0]] * 3
        )
        results = await small.search("c1", [1.0, 0.0], top_k=10)
        # Oldest ('a') should be evicted
        ids = {r["id"] for r in results}
        assert "a" not in ids
        assert "b" in ids
        assert "c" in ids

    @pytest.mark.asyncio
    async def test_search_empty_collection(self):
        results = await self.store.search("missing", [1.0, 0.0], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_fallback(self):
        await self.store.add_documents(
            "c1", ["a", "b"], ["alpha bravo", "charlie delta"], [[1.0, 0.0], [0.0, 1.0]]
        )
        results = await self.store.hybrid_search(
            "c1", "alpha", [1.0, 0.0], top_k=2, alpha=1.0
        )
        assert len(results) == 2
