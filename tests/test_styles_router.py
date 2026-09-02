import pytest
from fastapi.testclient import TestClient
from src.backend.server import app

client = TestClient(app)


def test_get_style_presets():
    """プリセット一覧エンドポイントのテスト"""
    response = client.get("/api/styles/presets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # ざまぁ等の主要ジャンルが含まれているか
    preset_ids = [p["id"] for p in data]
    assert "zarma" in preset_ids
    assert "aku_reijo" in preset_ids


def test_distill_style_api():
    """文体蒸留APIエンドポイントのテスト"""
    sample_text = """
    漆黒の鎧を纏った騎士がゆっくりと剣を抜いた。
    圧倒的な威圧感。空気が凍りつくような冷気が場を支配する。
    「貴様の力、見せてもらおうか」
    男は不敵に笑い、一瞬で間合いを詰めた。
    """
    response = client.post(
        "/api/styles/distill",
        json={"sample_text": sample_text, "name_hint": "黒騎士調"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "profile" in data
    assert data["profile"]["name"] == "黒騎士調"


def test_reformat_cadence_api():
    """音律・リズム整形APIエンドポイントのテスト"""
    input_text = "少年は逃げた。敵は追ってきた。恐怖で震えていた。しかし反撃を決意した。"
    response = client.post(
        "/api/styles/reformat",
        json={"text": input_text},
    )
    assert response.status_code == 200
    data = response.json()
    assert "reformatted_text" in data
    assert "stats" in data
    assert data["stats"]["total_sentences"] >= 3
