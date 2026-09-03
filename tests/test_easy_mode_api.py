import pytest

from src.backend.server import app



def test_gacha_api_validation_error(client):
    """キーワードが空の場合に422バリデーションエラーを返すことを検証"""
    response = client.post("/api/easy-mode/gacha", json={"genre": "", "keywords": []})
    assert response.status_code == 422


def test_gacha_api_success(client):
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


def test_digest_api_success(client):
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


def test_promote_api_success(client):
    """プロデューサー昇格APIが正常にレスポンスを返すことを検証"""
    # 1. ガチャ実行
    gacha_res = client.post(
        "/api/easy-mode/gacha",
        json={"genre": "ファンタジー", "keywords": ["剣", "魔法"], "temperature": 0.7},
    )
    req_id = gacha_res.json()["request_id"]
    plan_id = gacha_res.json()["plans"][0]["plan_id"]

    # 2. ダイジェスト実行して book_id 取得
    digest_res = client.post(
        "/api/easy-mode/digest",
        json={"request_id": req_id, "selected_plan_id": plan_id},
    )
    book_id = digest_res.json()["book_id"]

    # 3. 昇格実行
    response = client.post(
        "/api/easy-mode/promote",
        json={"book_id": book_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert f"/advanced/{book_id}" in data["redirect_url"]
    assert "state_token" in data


def test_reverse_generate_api(client):
    """逆算プロット生成APIが正常にレスポンスを返すことを検証"""
    response = client.post(
        "/easy_mode/reverse-generate",
        json={
            "answers": {
                "emotionalGoal": "triumph",
                "sacrifice": "peace",
                "coreConflict": "ideal_vs_reality",
                "openingHook": "isekai_awakening",
            },
            "targetEpisodes": 10,
            "genre": "ハイファンタジー (R15)",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "arcs" in data
    assert "episodes" in data
    assert len(data["arcs"]) >= 1
    assert len(data["episodes"]) == 10
    assert "catharsis_pattern" in data
    assert "catharsisPattern" in data


def test_export_with_data_api(client):
    """カスタムデータ付きZIPエクスポートAPIが正常にZIPを返すことを検証"""
    response = client.post(
        "/easy_mode/export-with-data?book_id=99",
        json={
            "title": "カスタムタイトル",
            "genre": "ハイファンタジー (R15)",
            "current_text": "カスタム本文内容です。",
            "character": {
                "name": "テスト主人公",
                "personality": "冷静沈着",
                "ability": "氷結魔法",
            },
        },
    )
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/zip"
    assert len(response.content) > 100

