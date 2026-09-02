"""Unit tests for EmbeddingService.get_embeddings_batch (Phase C)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.services.embedding_service import EmbeddingService


class TestEmbeddingServiceBatch:
    """Tests for batch embedding interface."""

    def _make(self, model_name="test-model"):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.model_name = model_name
        svc._client = None
        svc._cache = MagicMock()
        svc._cache.get.return_value = None
        return svc

    def test_get_embeddings_batch_empty(self):
        """Empty input → empty output."""
        svc = self._make()
        out = svc.get_embeddings_batch([])
        assert out == []

    def test_get_embeddings_batch_single(self):
        """Single element returns a list of length 1."""
        svc = self._make()
        out = svc.get_embeddings_batch(["hello"])
        assert len(out) == 1
        assert len(out[0]) == 1536

    def test_get_embeddings_batch_preserves_order(self):
        """Order is preserved even with mock client."""
        svc = self._make()
        mock_response_a = MagicMock()
        mock_response_a.data = [MagicMock(embedding=[0.1, 0.2, 0.3], index=0)]
        mock_response_b = MagicMock()
        mock_response_b.data = [MagicMock(embedding=[0.4, 0.5, 0.6], index=0)]
        call_count = {"n": 0}

        def fake_create(input, model):
            call_count["n"] += 1
            return mock_response_a if call_count["n"] == 1 else mock_response_b

        mock_client = MagicMock()
        mock_client.embeddings.create = fake_create
        svc._client = mock_client

        out = svc.get_embeddings_batch(["alpha", "bravo"], batch_size=1)
        assert len(out) == 2
        assert out[0] == [0.1, 0.2, 0.3]
        assert out[1] == [0.4, 0.5, 0.6]

    def test_get_embeddings_batch_respects_batch_size(self):
        """Batch size splits inputs into multiple API calls."""
        svc = self._make()
        svc._BATCH_SIZE = 2
        call_inputs = []

        def fake_create(input, model):
            call_inputs.append(list(input))
            r = MagicMock()
            r.data = [MagicMock(embedding=[0.0] * 4, index=i) for i in range(len(input))]
            return r

        mock_client = MagicMock()
        mock_client.embeddings.create = fake_create
        svc._client = mock_client

        out = svc.get_embeddings_batch(["a", "b", "c", "d", "e"], batch_size=2)
        assert len(out) == 5
        assert len(call_inputs) == 3  # 2 + 2 + 1
        assert call_inputs[0] == ["a", "b"]
        assert call_inputs[1] == ["c", "d"]
        assert call_inputs[2] == ["e"]

    def test_get_embeddings_batch_blank_inputs(self):
        """Blank inputs return zero vectors of the configured dimension."""
        svc = self._make()
        out = svc.get_embeddings_batch(["", "  ", "hello"])
        assert out[0] == [0.0] * 1536
        assert out[1] == [0.0] * 1536
        assert len(out[2]) == 1536
