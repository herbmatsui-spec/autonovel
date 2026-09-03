"""API エンドポイント契約テスト.

レスポンス形状の不変性を確認し、破壊的変更を検知する。
"""
import pytest
from fastapi.testclient import TestClient

print("[test module] About to import app", flush=True)
from src.backend.server import app

print("[test module] Creating TestClient", flush=True)
client = TestClient(app)
print("[test module] TestClient created", flush=True)


def test_graph_endpoint_response_shape():
    """/api/graph レスポンス形状の不変性"""
    resp = client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.json()

    # 必須トップレベルフィールド
    assert "graph_name" in data
    assert "nodes" in data
    assert "edges" in data

    # 型確認
    assert isinstance(data["graph_name"], str)
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)

    # ノード構造（存在する場合）
    if data["nodes"]:
        node = data["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "properties" in node
        assert isinstance(node["id"], str)
        assert isinstance(node["label"], str)
        assert isinstance(node["properties"], dict)

    # エッジ構造（存在する場合）
    if data["edges"]:
        edge = data["edges"][0]
        assert "source" in edge
        assert "target" in edge
        assert "type" in edge
        assert "properties" in edge
        assert isinstance(edge["source"], str)
        assert isinstance(edge["target"], str)
        assert isinstance(edge["type"], str)
        assert isinstance(edge["properties"], dict)


def test_graph_chunks_endpoint(client):
    """/api/graph/chunks レスポンス形状"""
    import os
    from sqlalchemy import inspect
    from src.backend.database import SessionLocal
    resp = client.get("/api/graph/chunks")
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)

    if data:
        chunk = data[0]
        required_fields = ["id", "chapter_id", "chunk_index", "content", "has_embedding", "created_at"]
        for field in required_fields:
            assert field in chunk
        assert isinstance(chunk["chapter_id"], int)
        assert isinstance(chunk["chunk_index"], int)
        assert isinstance(chunk["has_embedding"], bool)


def test_rag_context_endpoint_response_shape():
    """POST /api/graph/rag/context レスポンス形状"""
    resp = client.post(
        "/api/graph/rag/context",
        json={
            "current_prompt": "テストプロンプト",
            "character_name": "主人公",
            "additional_entities": ["聖剣"]
        }
    )
# GraphRAG 無劫環境でも 200 返却
    assert resp.status_code == 200
    data = resp.json()

    required_fields = ["graph_context", "vector_context", "stats", "token_estimate"]
    for field in required_fields:
        assert field in data

    assert isinstance(data["graph_context"], str)
    assert isinstance(data["vector_context"], str)
    assert isinstance(data["stats"], dict)
    assert isinstance(data["token_estimate"], int)


def test_rag_hybrid_search_endpoint():
    """POST /api/graph/rag/hybrid-search レスポンス形状"""
    resp = client.post(
        "/api/graph/rag/hybrid-search",
        json={
            "query": "テストクエリ",
            "core_entities": ["主人公"],
            "top_k": 5,
            "alpha": 0.5,
            "beta": 0.3,
            "gamma": 0.2
        }
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "query" in data
    assert "results" in data
    assert "count" in data
    assert "elapsed_ms" in data

    assert isinstance(data["results"], list)
    assert isinstance(data["count"], int)
    assert isinstance(data["elapsed_ms"], int)

    if data["results"]:
        result = data["results"][0]
        required_fields = ["id", "content", "metadata", "source", "score", "similarity"]
        for field in required_fields:
            assert field in result


def test_rag_episode_endpoint():
    """POST /api/graph/rag/episode レスポンス形状"""
    resp = client.post(
        "/api/graph/rag/episode",
        params={
            "character_name": "主人公",
            "additional_entities": ["聖剣"],
            "top_k": 3
        }
    )
    assert resp.status_code == 200
    data = resp.json()

    required_fields = ["graph", "vector", "stats", "token_estimate", "top_k"]
    for field in required_fields:
        assert field in data


def test_rag_stats_endpoint():
    """GET /api/graph/rag/stats レスポンス形状"""
    resp = client.get("/api/graph/rag/stats")
    assert resp.status_code == 200
    data = resp.json()

    # stats は dict
    assert isinstance(data, dict)


def test_graph_stats_endpoint():
    """GET /api/graph/stats レスポンス形状"""
    resp = client.get("/api/graph/stats")
    # GraphRAG 無効環境では 400 または 200（エラー情報含む）
    assert resp.status_code in (200, 400)

    if resp.status_code == 200:
        data = resp.json()
        required = ["node_count", "edge_count", "labels", "relationship_types"]
        for field in required:
            assert field in data


def test_graph_neighbors_endpoint():
    """POST /api/graph/search/neighbors レスポンス形状"""
    resp = client.post(
        "/api/graph/search/neighbors",
        json={
            "node_name": "主人公",
            "max_depth": 2,
            "limit": 10
        }
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "node_name" in data
    assert "neighbors" in data
    assert "count" in data
    assert isinstance(data["neighbors"], list)
    assert isinstance(data["count"], int)


def test_pipeline_process_endpoint():
    """POST /api/graph/pipeline/process レスポンス形状"""
    resp = client.post(
        "/api/graph/pipeline/process",
        json={
            "chapter_id": 1,
            "chapter_text": "テスト本文",
            "idempotency_key": "test_key_1"
        }
    )
    assert resp.status_code == 200
    data = resp.json()

    required = ["chapter_id", "success", "chunks_created", "entities_created", "relationships_created"]
    for field in required:
        assert field in data


def test_pipeline_batch_endpoint():
    """POST /api/graph/pipeline/batch レスポンス形状"""
    resp = client.post(
        "/api/graph/pipeline/batch",
        json={
            "chapters": [
                {"chapter_id": 1, "chapter_text": "第1話", "idempotency_key": "k1"},
                {"chapter_id": 2, "chapter_text": "第2話", "idempotency_key": "k2"}
            ],
            "continue_on_error": True
        }
    )
    assert resp.status_code == 200
    data = resp.json()

    required = ["chapters_processed", "chunks_created", "entities_created", "relationships_created", "errors", "elapsed_ms"]
    for field in required:
        assert field in data


def test_health_endpoint():
    """/health エンドポイント"""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("healthy", "ok")


def test_openapi_schema_available():
    """OpenAPI スキーマが取得可能"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "openapi" in schema
    assert "paths" in schema
    # Graph 関連エンドポイント存在確認
    assert "/api/graph" in schema["paths"]
    assert "/api/graph/rag/context" in schema["paths"]