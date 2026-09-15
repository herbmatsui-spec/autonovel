from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.observability.health import metrics
from src.backend.observability.metrics import (
    PathNormalizer,
    metrics_endpoint,
    record_generation_task,
    record_http_metrics,
    record_llm_call,
    update_db_pool_metrics,
    update_huey_queue_depth,
)


def test_path_normalizer():
    normalizer = PathNormalizer()
    assert normalizer.normalize("/api/books/123") == "/api/books/{id}"
    assert normalizer.normalize("/api/episodes/45") == "/api/episodes/{id}"
    assert normalizer.normalize("/api/tasks/task-abc-123") == "/api/tasks/{id}"
    assert normalizer.normalize("/api/v1/health") == "/api/v1/health"


def test_record_http_and_llm_metrics():
    # 例外が出ずに Prometheus メトリクスに記録されることを確認
    record_http_metrics("GET", "/api/v1/health", 200, 0.05)
    record_generation_task("full_auto", "completed", 12.3)
    record_llm_call("gemini-1.5-pro", "success", prompt_tokens=100, completion_tokens=200)
    update_db_pool_metrics(active=5, idle=2)
    update_huey_queue_depth(3)


@pytest.mark.asyncio
async def test_metrics_endpoint_response():
    resp = await metrics_endpoint()
    assert resp.status_code == 200
    assert "text/plain" in resp.media_type or "version=0.0.4" in resp.media_type
    assert len(resp.body) > 0


def test_health_in_memory_metrics():
    metrics.reset_for_testing()
    assert metrics.get("health_checks") == 0
    metrics.increment("health_checks", 2)
    assert metrics.get("health_checks") == 2
    snapshot = metrics.snapshot()
    assert snapshot["health_checks"] == 2
    metrics.reset_for_testing()
    assert metrics.get("health_checks") == 0


def test_router_module_imports():
    """主要ルーターモジュールが安全にインポートできることを検証（スモークテスト）"""
    import importlib

    routers = [
        "src.backend.routers.books",
        "src.backend.routers.episodes",
        "src.backend.routers.health",
        "src.backend.routers.metrics",
        "src.backend.routers.system",
    ]
    for r in routers:
        mod = importlib.import_module(r)
        assert hasattr(mod, "router")
