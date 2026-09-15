"""
GlobalAuthMiddleware の動作検証テスト
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from src.backend.config import settings
from src.backend.middleware.auth_middleware import GlobalAuthMiddleware
from src.backend.security.jwt import create_access_token


@pytest.fixture
def test_app():
    app = FastAPI()
    app.add_middleware(GlobalAuthMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/protected-resource")
    def protected():
        return {"data": "secret"}

    @app.options("/api/protected-resource")
    def options():
        return {"allow": "GET, OPTIONS"}

    return app


def test_public_path_allows_unauthenticated(test_app):
    client = TestClient(test_app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_protected_path_rejects_unauthenticated(test_app):
    client = TestClient(test_app)
    res = client.get("/api/protected-resource")
    assert res.status_code == 401
    assert res.json() == {"detail": "認証が必要です"}


def test_protected_path_allows_valid_jwt(test_app):
    client = TestClient(test_app)
    token = create_access_token(user_id=1, role="user")
    res = client.get("/api/protected-resource", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == {"data": "secret"}


def test_protected_path_rejects_invalid_jwt(test_app):
    client = TestClient(test_app)
    res = client.get("/api/protected-resource", headers={"Authorization": "Bearer invalid.token.payload"})
    assert res.status_code == 401
    assert res.json() == {"detail": "無効または期限切れのトークンです"}


def test_options_preflight_bypasses_auth(test_app):
    client = TestClient(test_app)
    res = client.options("/api/protected-resource")
    assert res.status_code == 200


def test_auth_disabled_bypasses_auth(test_app, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)
    client = TestClient(test_app)
    res = client.get("/api/protected-resource")
    assert res.status_code == 200
    assert res.json() == {"data": "secret"}
