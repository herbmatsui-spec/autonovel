"""未認証 401 時の CORS ヘッダー検証テスト"""
from fastapi.testclient import TestClient
from src.backend.server import app

def test_unauthorized_response_contains_cors_headers():
    client = TestClient(app)
    response = client.get(
        "/api/books",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 401
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
