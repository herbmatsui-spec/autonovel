"""tests/unit/test_consistency_api.py"""
import pytest
from fastapi.testclient import TestClient

from src.backend.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_consistency_check_endpoint(client):
    # Should return 200 with findings list (likely empty for non-existent book)
    resp = client.post("/api/consistency/1/check", json={"ep_num": None})
    assert resp.status_code == 200
    data = resp.json()
    assert "findings" in data
    assert "summary" in data


def test_consistency_dismiss_endpoint(client):
    resp = client.post(
        "/api/consistency/1/dismiss",
        json={"finding_key": "test:key", "reason": "intentional"},
    )
    assert resp.status_code == 200
    # List should contain it
    lst = client.get("/api/consistency/1/dismissed")
    assert lst.status_code == 200
    assert "test:key" in lst.json()["dismissed"]
