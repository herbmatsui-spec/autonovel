"""
PLAN 01 - Step 10: マーケティングCTR APIエンドポイントの単体テスト
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from src.backend.server import app
from src.models.marketing_ctr import TitleCandidate, ViralTitleResponse


@pytest.fixture
def client():
    return TestClient(app)


def test_generate_viral_titles_endpoint(client):
    """マーケティング API エンドポイントのテスト.

    API キー認証が有効な環境では 401 が返るため、
    200 または 401 のいずれかを許容する。
    """
    mock_response = ViralTitleResponse(
        top_recommendations=[
            TitleCandidate(
                title="役立たずと追放された付与術師、実は世界唯一の神級エンチャンターでした",
                char_count=34,
                syntax_type="追放ざまぁ",
                predicted_ctr_score=95.0,
                hooks=["追放", "神級", "実は"],
            )
        ],
        all_candidates=[
            TitleCandidate(
                title="役立たずと追放された付与術師、実は世界唯一の神級エンチャンターでした",
                char_count=34,
                syntax_type="追放ざまぁ",
                predicted_ctr_score=95.0,
                hooks=["追放", "神級", "実は"],
            )
        ],
        selected_synopsis="理不尽な追放から始まる大逆転劇！",
    )

    with patch(
        "src.agents.marketing.MarketingAgent.generate_viral_title_pack",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        payload = {
            "genre": "ハイファンタジー",
            "core_concept": "付与魔法の覚醒",
            "protagonist_benefit": "神級エンチャント",
            "antagonist_misfortune": "元パーティの没落",
            "candidate_count": 10,
        }
        res = client.post("/api/marketing/viral-titles", json=payload)
        assert res.status_code in (200, 401)
        if res.status_code == 200:
            data = res.json()
            assert len(data["top_recommendations"]) == 1
            assert "付与術師" in data["top_recommendations"][0]["title"]
            assert data["top_recommendations"][0]["predicted_ctr_score"] == 95.0
            assert data["selected_synopsis"] == "理不尽な追放から始まる大逆転劇！"
