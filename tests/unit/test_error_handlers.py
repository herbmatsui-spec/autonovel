"""Tests for error handlers in src.backend.error_handlers."""

import pytest
from unittest.mock import MagicMock
from src.backend.error_handlers import generic_error_handler
from src.backend.config import settings


@pytest.mark.asyncio
async def test_generic_error_handler_masking_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    dummy_request = MagicMock()
    dummy_request.url.path = "/api/test-endpoint"

    response = await generic_error_handler(dummy_request, ValueError("Sensitive DB Connection Error"))
    assert response.status_code == 500
    import json
    body = json.loads(response.body.decode("utf-8"))
    assert body["detail"] == "Internal server error occurred."
    assert "Sensitive DB Connection Error" not in body["detail"]


@pytest.mark.asyncio
async def test_generic_error_handler_detail_in_development(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    dummy_request = MagicMock()
    dummy_request.url.path = "/api/test-endpoint"

    response = await generic_error_handler(dummy_request, ValueError("Developer Debug Info"))
    assert response.status_code == 500
    import json
    body = json.loads(response.body.decode("utf-8"))
    assert body["detail"] == "Developer Debug Info"
