"""
Tests for timing-safe API key comparison in AuthMiddleware.
Verifies that secrets.compare_digest / hmac.compare_digest is used for constant-time comparisons.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.backend.middleware.auth_middleware import AuthMiddleware


@pytest.fixture
def mock_settings():
    with patch("src.backend.middleware.auth_middleware.settings") as mock_set:
        mock_set.AUTH_DISABLED = False
        mock_set.ALLOWED_API_KEYS = "secret-key-1,secret-key-2"
        yield mock_set


@pytest.mark.asyncio
async def test_timing_safe_api_key_match(mock_settings):
    """Valid API Key in X-API-Key header should pass via compare_digest."""
    middleware = AuthMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=Response(status_code=200))
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/projects",
        "headers": [(b"x-api-key", b"secret-key-1")],
    }
    request = Request(scope)

    with patch("secrets.compare_digest", wraps=__import__("secrets").compare_digest) as mock_cd:
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert mock_cd.called, "secrets.compare_digest must be called for API key verification"


@pytest.mark.asyncio
async def test_timing_safe_api_key_mismatch(mock_settings):
    """Invalid API Key in X-API-Key header should be rejected."""
    middleware = AuthMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=Response(status_code=200))
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/projects",
        "headers": [(b"x-api-key", b"wrong-key")],
    }
    request = Request(scope)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 401
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_timing_safe_bearer_api_key_match(mock_settings):
    """Valid API Key passed as Bearer token should pass via compare_digest."""
    middleware = AuthMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=Response(status_code=200))
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/projects",
        "headers": [(b"authorization", b"Bearer secret-key-2")],
    }
    request = Request(scope)

    with patch("secrets.compare_digest", wraps=__import__("secrets").compare_digest) as mock_cd:
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        assert mock_cd.called, "secrets.compare_digest must be called for Bearer API key verification"
