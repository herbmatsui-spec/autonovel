"""
E2E integration test for the Kakuyomu Viral Title & CTR Optimization Pipeline.
Tests the full flow: Request -> Router -> Agent -> Syntax Extractor -> CTR Scorer -> Synopsis Generator -> Response.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from src.backend.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_title_ctr_pipeline_e2e(client):
    """
    Verify complete viral title generation and CTR scoring pipeline for an exile/reversal trope.
    Requirements:
    - 30 candidate titles generated and scored.
    - Top 3 candidates score at least 75 points.
    - Top recommendations have syntax pattern match and emotional trigger keywords.
    - Synopsis properly generated and attached.
    """
    # 30 candidate titles to be returned by LLM generate_json
    mock_candidates = [
        {
            "title": "無能と罵られ勇者パーティーを追放された付与術師、実は世界唯一の【神域付与】で無自覚に最強無双〜今更戻ってきてくれと泣きつかれてももう遅い〜",
            "syntax_type": "追放ざまぁ",
        },
        {
            "title": "【追放されたSランク冒険者、実は全属性の覇王だった】無能扱いしたギルドが崩壊寸前らしいが、俺は辺境で気ままにスローライフを満喫中",
            "syntax_type": "追放スローライフ",
        },
        {
            "title": "役立たずと婚約破棄された公爵令嬢、隣国の冷酷皇帝に溺愛されて覚醒する〜復讐は自分でやり遂げるのでお構いなく〜",
            "syntax_type": "婚約破棄逆転",
        },
        {
            "title": "雑用係と追放された少年、拾った魔剣が古代竜王の化身だった件。第二の人生で無双して見返してやる",
            "syntax_type": "追放逆転",
        },
        {
            "title": "万年Eランクの無能と笑われたおっさん、実は人類最強の【即死魔法】の使い手だった〜今更勇者パーティーに懇願されても断る〜",
            "syntax_type": "隠れ最強",
        },
    ] + [
        {
            "title": f"追放された不遇職の鍛冶師、チートスキル【神器創造】でスローライフを送るつもりが世界最強の英雄になっていた件（第{i}幕）",
            "syntax_type": "追放成り上がり",
        }
        for i in range(6, 31)
    ]

    mock_synopsis = (
        "【理不尽な追放】無能と罵られ、最果てのダンジョンに置き去りにされたアルト。\n"
        "【覚醒と無双】だが死の間際に発現したのは、世界の理すら書き換える『神域付与』だった！\n"
        "【ざまぁと快進撃】気づいた時には全てが手遅れ。今さら勇者たちが泣きついてきても絶対に許さない！"
    )

    with patch("src.backend.routers.marketing_ctr.get_llm_adapter") as mock_get_adapter:
        mock_llm = AsyncMock()
        mock_llm.generate_json.return_value = {"candidates": mock_candidates}
        mock_llm.generate_text.return_value = mock_synopsis
        mock_get_adapter.return_value = mock_llm

        payload = {
            "genre": "異世界ファンタジー",
            "core_concept": "無能と罵られ勇者パーティーを追放されたが実は世界唯一の神域付与術師だった",
            "protagonist_benefit": "神域付与と無限魔力による絶対無双",
            "antagonist_misfortune": "無能と罵った勇者パーティーがダンジョンで壊滅危機",
            "candidate_count": 30,
        }

        response = client.post("/api/marketing/viral-titles", json=payload)
        assert response.status_code == 200, f"Failed with: {response.text}"

        data = response.json()

        # Contract assertions
        assert len(data["all_candidates"]) == 30
        assert len(data["top_recommendations"]) >= 3
        assert len(data["selected_synopsis"]) > 0

        # Quality & CTR Score assertions: Top 3 candidates score at least 75 points
        for idx, cand in enumerate(data["top_recommendations"][:3]):
            assert cand["predicted_ctr_score"] >= 75.0, (
                f"Candidate {idx} ({cand['title']}) score {cand['predicted_ctr_score']} < 75.0"
            )
            assert cand["char_count"] >= 30, (
                f"Candidate {cand['title']} char_count {cand['char_count']} < 30"
            )
            assert len(cand["hooks"]) >= 1, (
                f"Candidate {cand['title']} hooks is empty"
            )

        # Candidates must be ordered by score descending
        all_scores = [c["predicted_ctr_score"] for c in data["all_candidates"]]
        assert all_scores == sorted(all_scores, reverse=True)

        # Synopsis must contain emotional beats
        assert "追放" in data["selected_synopsis"]
