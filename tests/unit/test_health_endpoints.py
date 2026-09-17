from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.backend.routers.health import router
import src.backend.routers.health
from unittest.mock import patch
from src.backend.health.checks import HealthCheckResult, HealthStatus


def test_liveness_endpoint_returns_200():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_readiness_endpoint_returns_503_on_db_failure():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with patch.object(src.core.container.AppContainer, 'db') as mock_db_container, \
         patch.object(src.backend.routers.health, 'check_database') as mock_check_db:
        # Mock the database container to return a mock db manager
        mock_db_manager = {}
        mock_db_container.return_value = mock_db_manager

        # Mock the check_database function to return an error result
        mock_check_db.return_value = HealthCheckResult(
            status=HealthStatus.ERROR,
            error="Connection refused",
        )

        response = client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["database"] == "error"
