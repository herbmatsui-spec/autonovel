"""
Regression test for Step 13: Proper HTTP status code handling and DB checking in health.py.
Verifies that:
1. /health/live returns HTTP 200 with alive status.
2. /health/ready returns HTTP 200 when database check succeeds.
3. /health/ready returns HTTP 503 (NOT 200 with tuple body) when database check fails.
"""

from unittest.mock import patch, AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.health import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_health_live_endpoint():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_health_ready_endpoint_healthy():
    with patch("src.backend.observability.health.check_database", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = {"status": "ok", "type": "sqlite"}
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready_endpoint_unhealthy_returns_503():
    with patch("src.backend.observability.health.check_database", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = {"status": "error", "code": "DB_UNAVAILABLE"}
        response = client.get("/health/ready")
        # Critical regression check: MUST be status code 503, NOT 200
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not ready"
        assert data["error"] == "DB_UNAVAILABLE"


@pytest.mark.asyncio
async def test_health_ready_endpoint_exception_returns_503():
    with patch("src.backend.observability.health.check_database", side_effect=RuntimeError("Connection refused")):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not ready"
        assert "Connection refused" in data["error"]
