from fastapi.testclient import TestClient

from src.backend.server import app

client = TestClient(app)


def test_gacha_api_validation_error():
    """キーワードが空の場合に422バリデーションエラーを返すことを検証"""
    response = client.post("/api/easy-mode/gacha", json={"genre": "", "keywords": []})
    assert response.status_code == 422


def test_gacha_api_success():
    """正常に3案ガチャが生成されることを検証"""
    response = client.post(
        "/api/easy-mode/gacha",
        json={"genre": "ファンタジー", "keywords": ["無双", "魔法"], "temperature": 0.7},
    )
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert len(data["plans"]) == 3
    plan_types = [p["plan_type"] for p in data["plans"]]
    assert "royal" in plan_types
    assert "curveball" in plan_types
    assert "dark" in plan_types


def test_digest_api_success():
    """ダイジェスト生成APIが正常にレスポンスを返すことを検証"""
    response = client.post(
        "/api/easy-mode/digest",
        json={"request_id": "test_req", "selected_plan_id": "test_plan"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "book_id" in data
    assert "synopsis" in data
    assert "episode_1_text" in data
    assert "climax_preview_text" in data
    assert data["status"] in ["completed", "failed"]


def test_promote_api_success():
    """プロデューサー昇格APIが正常にレスポンスを返すことを検証"""
    response = client.post(
        "/api/easy-mode/promote",
        json={"book_id": "test_book_123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["redirect_url"] == "/advanced/test_book_123"
    assert "state_token" in data
