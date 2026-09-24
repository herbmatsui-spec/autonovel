import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.health import router as health_router

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(health_router)
    return TestClient(app)

def test_live_endpoint(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"

def test_ready_endpoint(client):
    # In this test, we assume the dependencies are up (we have not implemented actual checks).
    # The endpoint will return "ready" if no exception is raised.
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"