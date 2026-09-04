"""Contract テスト用共有フィクスチャと設定."""
from __future__ import annotations

import pytest
from src.backend import database
from src.backend.server import app
from fastapi.testclient import TestClient


@pytest.fixture
def contract_client():
    """Contract テスト用の TestClient フィクスチャ.
    
    OpenAPI スキーマを取得するために使用します。
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def openapi_schema(contract_client):
    """OpenAPI スキーマを取得するフィクスチャ."""
    response = contract_client.get("/openapi.json")
    assert response.status_code == 200, "OpenAPI スキーマを取得できませんでした"
    return response.json()