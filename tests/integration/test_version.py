"""
Integration test for version synchronization.

Verifies that the API version reported by FastAPI matches the settings version.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_api_version_matches_settings():
    """Test that the OpenAPI spec version matches settings.app_version."""
    from config.settings import get_settings
    from src.backend.server import create_app

    settings = get_settings()
    app = create_app()
    client = TestClient(app)

    # Get the OpenAPI spec
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_spec = response.json()
    api_version = openapi_spec.get("info", {}).get("version")

    # Version should match settings
    assert api_version == settings.app_version, (
        f"API version ({api_version}) does not match settings.app_version ({settings.app_version})"
    )


@pytest.mark.integration
def test_version_endpoint_if_exists():
    """Test version endpoint if available."""
    from src.backend.server import create_app

    app = create_app()
    client = TestClient(app)

    # Check if there's a version endpoint
    response = client.get("/api/version")
    if response.status_code == 200:
        data = response.json()
        from config.settings import get_settings
        settings = get_settings()
        assert data.get("version") == settings.app_version