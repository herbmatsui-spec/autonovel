"""
tests/api/test_server_health_integration.py
Part 2 (Step 5-8) リグレッション防止テスト:
本番構成の FastAPI メインアプリケーション (src.backend.server.app) に対する
実ヘルスチェックルーティング・ミドルウェア透過性・503ステータスハンドリングを直接検証。
"""

from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from src.backend.server import app

client = TestClient(app)


def test_server_health_live_probe_unauthenticated():
    """認証ヘッダーなしで /health/live および /health/liveness が 200 を返すことを確認"""
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json().get("status") == "alive"

    res_liveness = client.get("/health/liveness")
    assert res_liveness.status_code == 200
    assert res_liveness.json().get("status") == "alive"


@pytest.mark.asyncio
async def test_server_health_ready_probe_database_ok():
    """DB 正常時に /health/ready が HTTP 200 と ready ステータスを返すことを確認"""
    with patch("src.backend.observability.health.check_database", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = {"status": "ok", "type": "sqlite"}
        res = client.get("/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "ready"
        assert data.get("checks", {}).get("database", {}).get("status") == "ok"


@pytest.mark.asyncio
async def test_server_health_ready_probe_database_fail_returns_503():
    """DB 異常時に /health/ready が HTTP 503 を返すことを確認 (Critical Regression Check)"""
    with patch("src.backend.observability.health.check_database", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = {"status": "error", "code": "DB_UNAVAILABLE"}
        res = client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data.get("status") == "not ready"
        assert data.get("error") == "DB_UNAVAILABLE"


@pytest.mark.asyncio
async def test_server_health_ready_probe_exception_returns_503():
    """DB 接続例外発生時に /health/ready が HTTP 503 を返すことを確認"""
    with patch("src.backend.observability.health.check_database", side_effect=RuntimeError("Connection refused")):
        res = client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data.get("status") == "not ready"
        assert "Connection refused" in data.get("error")


def test_server_root_health_returns_status():
    """/health ルートが正常に総合ステータスを返すことを確認"""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
