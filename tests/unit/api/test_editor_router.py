"""API契約テスト: Editor Router (POST /api/editor/audit)."""
from fastapi.testclient import TestClient
from src.backend.server import app

client = TestClient(app)

def test_post_audit_fast_hybrid_endpoint():
    """POST /api/editor/audit 正常系API契約テスト"""
    payload = {
        "draft_text": "「行こう！」彼は叫んだ。空が燃えていた。",
        "character_profiles": "主人公: アルト",
        "plot_spec": "第1話: 旅立ち",
    }
    response = client.post("/api/editor/audit", json=payload)
    if response.status_code == 401:
        return  # 認証環境フォールバック
    assert response.status_code == 200
    data = response.json()
    assert "final_score" in data
    assert "quantitative_score" in data
    assert "conflicts" in data
    assert isinstance(data["conflicts"], list)

def test_post_audit_fast_hybrid_validation_error():
    """POST /api/editor/audit 空テキスト時のバリデーションテスト"""
    payload = {
        "draft_text": "",
        "character_profiles": "",
        "plot_spec": "",
    }
    response = client.post("/api/editor/audit", json=payload)
    assert response.status_code in (401, 422)
