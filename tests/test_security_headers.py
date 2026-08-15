"""セキュリティヘッダーミドルウェアのテスト"""
from fastapi.testclient import TestClient

from src.backend.server import app


def test_security_headers_present():
    """セキュリティヘッダーが正しく設定されていることを確認"""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")
    assert "includeSubDomains" in response.headers.get("Strict-Transport-Security", "")


def test_security_headers_on_error():
    """エラーレスポンスにもセキュリティヘッダーが設定されていることを確認"""
    client = TestClient(app)
    response = client.get("/nonexistent")

    assert response.status_code == 404
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")


def test_security_headers_on_auth_error():
    """認証エラー時にもセキュリティヘッダーが設定されていることを確認"""
    client = TestClient(app)
    # auth が必要なエンドポイントに無効なキーでアクセス
    response = client.get("/api/health", headers={"X-API-Key": "invalid-key"})

    # 404 (エンドポイントが存在しない) または 403 (認証エラー) のいずれか
    # いずれにせよセキュリティヘッダーが設定されていること
    assert response.status_code in (403, 404)
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")
