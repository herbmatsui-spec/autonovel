"""Unit tests for chunk_ingestion helper."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.services.chunk_ingestion import upsert_chunks
from src.services.vector_store import InMemoryFallbackStore


def _fake_chunk(id: str = "x", content: str = "hello", chapter_id: int = 1, chunk_index: int = 0):
    c = MagicMock()
    c.id = id
    c.content = content
    c.chapter_id = chapter_id
    c.chunk_index = chunk_index
    c.chunk_metadata = None
    return c


class TestUpsertChunks:
    @pytest.mark.asyncio
    async def test_empty_chunks(self):
        store = InMemoryFallbackStore()
        n = await upsert_chunks(store, [], collection="c1")
        assert n == 0

    @pytest.mark.asyncio
    async def test_upserts_three(self):
        store = InMemoryFallbackStore()
        chunks = [
            _fake_chunk(id="1", content="alpha", chapter_id=1, chunk_index=0),
            _fake_chunk(id="2", content="bravo", chapter_id=1, chunk_index=1),
            _fake_chunk(id="3", content="charlie", chapter_id=2, chunk_index=0),
        ]
        n = await upsert_chunks(store, chunks, collection="c1")
        assert n == 3
        results = await store.search("c1", [1.0] + [0.0] * 1535, top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_metadata_includes_chapter_id(self):
        store = InMemoryFallbackStore()
        chunks = [_fake_chunk(id="1", content="x", chapter_id=42, chunk_index=3)]
        await upsert_chunks(store, chunks, collection="c1")
        # metadata is queryable via search result
        results = await store.search("c1", [1.0] + [0.0] * 1535, top_k=1)
        assert results[0]["metadata"]["chapter_id"] == 42
        assert results[0]["metadata"]["chunk_index"] == 3
