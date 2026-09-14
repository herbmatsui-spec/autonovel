"""
PLAN 01 - Step 9: MarketingAgent.generate_viral_title_pack の単体テスト
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.agents.marketing import MarketingAgent
from src.models.marketing_ctr import ViralTitleRequest, ViralTitleResponse


@pytest.mark.asyncio
async def test_generate_viral_title_pack_success():
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock(
        return_value=[
            {"title": "役立たずと追放された付与術師、実は世界唯一の神級エンチャンターでした", "syntax_type": "追放ざまぁ"},
            {"title": "ただの田舎貴族ですが、なぜか周囲が世界最強の黒幕だと勘違いして崇めてきます", "syntax_type": "勘違い無双"},
            {"title": "普通の冒険者", "syntax_type": "一般"},
        ]
    )
    mock_llm.generate_text = AsyncMock(
        return_value="理不尽にパーティを追い出された男が、最強の力で無双する爽快成り上がりストーリー！"
    )

    mock_pm = MagicMock()
    mock_pm.build_viral_title_prompt = AsyncMock(return_value="TITLE_PROMPT")
    mock_pm.build_viral_synopsis_prompt = AsyncMock(return_value="SYNOPSIS_PROMPT")

    agent = MarketingAgent(llm=mock_llm, prompt_manager=mock_pm)

    req = ViralTitleRequest(
        genre="ハイファンタジー",
        core_concept="付与魔法の万能覚醒",
        protagonist_benefit="神級エンチャント",
        antagonist_misfortune="元パーティの没落",
        candidate_count=10,
    )

    response: ViralTitleResponse = await agent.generate_viral_title_pack(req)

    assert len(response.all_candidates) == 3
    # スコア降順に並んでいること
    assert response.all_candidates[0].predicted_ctr_score >= response.all_candidates[-1].predicted_ctr_score
    # 上位推薦案が1つ以上あること
    assert len(response.top_recommendations) >= 1
    assert "付与術師" in response.top_recommendations[0].title or "黒幕" in response.top_recommendations[0].title
    # あらすじが生成されていること
    assert "爽快成り上がり" in response.selected_synopsis
