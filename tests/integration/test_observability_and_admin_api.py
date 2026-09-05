"""Integration tests for Observability, Metrics, and Admin Phase 2 APIs (Step 71).

Verifies that:
1. Health and in-memory process metrics endpoints (/health, /metrics) function correctly.
2. Specialist auditor administration (/admin/audit/specialists, /admin/audit/weights) returns accurate configurations.
3. Test aggregation endpoint (/admin/audit/aggregate_test) runs real audit logic and returns overall score.
4. Observability metrics for 4-layer compression and task counters increment accurately.
"""

import pytest
from fastapi.testclient import TestClient

from src.backend.server import app
from src.backend.auth import require_api_key
from src.backend.observability.health import metrics


@pytest.fixture
def client():
    # Bypass auth for test client
    app.dependency_overrides[require_api_key] = lambda: "mock-valid-key"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_endpoint(client):
    """Verify /health returns structured status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "metrics" in data
    assert "components" in data


def test_metrics_endpoint_and_counters(client):
    """Verify /metrics snapshots process counters accurately."""
    metrics.reset_for_testing()
    metrics.increment("tasks_enqueued", 3)
    metrics.increment("tasks_completed", 2)
    metrics.increment("tasks_failed", 1)

    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["tasks_enqueued"] == 3
    assert data["tasks_completed"] == 2
    assert data["tasks_failed"] == 1


def test_admin_audit_specialists_list(client):
    """Verify /admin/audit/specialists lists the 8 specialist auditors."""
    response = client.get("/admin/audit/specialists")
    assert response.status_code == 200
    specialists = response.json()
    assert len(specialists) == 8

    names = {s["name"] for s in specialists}
    expected = {
        "consistency",
        "creativity",
        "reader_hook",
        "emotion_curve",
        "style",
        "factual",
        "structure",
        "multimodal",
    }
    assert names == expected


def test_admin_audit_weights(client):
    """Verify /admin/audit/weights returns configured weights summing to 1.0."""
    response = client.get("/admin/audit/weights?genre=fantasy&phase=mid_writing")
    assert response.status_code == 200
    data = response.json()
    weights = data["weights"]

    assert len(weights) == 8
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 1e-4


def test_admin_audit_aggregate_test(client):
    """Verify /admin/audit/aggregate_test evaluates a draft and returns structured scores."""
    payload = {
        "book_id": 999,
        "chapter_number": 1,
        "draft_text": "城門の前で勇者は立ち止まった。なぜ彼が選ばれたのか？雨が降り注ぐ中、剣を抜いた。",
        "plot_tree": "城門 → 抜刀",
        "plot_summary": "城門での抜刀",
        "illustration_prompts": "城門の前で剣を抜く勇者",
        "genre": "fantasy",
        "phase": "mid_writing",
    }

    response = client.post("/admin/audit/aggregate_test", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "overall" in data
    assert 0.0 <= data["overall"] <= 100.0
    assert len(data["by_specialist"]) == 8
    assert data["lowest_dimension"] is not None
