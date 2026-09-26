"""_vector_store の遅延初期化が、差し込み優先で動くことの回帰テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.graph_pipeline import GraphPipelineService
from src.services.rag.rag_service import GraphRAGService


def test_rag_service_uses_injected_store_without_default():
    injected = MagicMock()
    svc = GraphRAGService(vector_store=injected, reranker=MagicMock())
    with patch("src.services.rag.rag_service.get_default_store") as mock_default:
        assert svc._vector_store is injected
    mock_default.assert_not_called()


def test_graph_pipeline_uses_injected_store_without_default():
    injected = MagicMock()
    svc = GraphPipelineService(enable_vector_store=True)
    svc._vector_store = injected
    with patch("src.services.graph_pipeline.get_default_store") as mock_default:
        assert svc._vector_store is injected
    mock_default.assert_not_called()


def test_graph_pipeline_disabled_returns_none():
    svc = GraphPipelineService(enable_vector_store=False)
    with patch("src.services.graph_pipeline.get_default_store") as mock_default:
        assert svc._vector_store is None
    mock_default.assert_not_called()
