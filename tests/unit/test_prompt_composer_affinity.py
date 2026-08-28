"""
tests/unit/test_prompt_composer_affinity.py - Phase 2: Acting Direction Injection in PromptComposer
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.schemas.ux_schemas import AffinityData
from src.agents.prompt_composer import PromptComposer


def test_prompt_composer_build_acting_direction():
    """ステップ 26〜31: 各 mood に対する Acting 指示の生成テスト"""
    mock_agent = MagicMock()
    composer = PromptComposer(agent=mock_agent)

    # 1. 警戒期 (wary)
    wary_data = AffinityData(character_name="エリス", affinity_score=30.0, wariness_score=70.0, current_mood="wary")
    wary_text = composer._build_acting_direction(wary_data)
    assert "エリス" in wary_text
    assert "wary" in wary_text
    assert "距離を保ち" in wary_text

    # 2. ツンデレ期 (tsundere)
    tsun_data = AffinityData(character_name="エリス", affinity_score=60.0, wariness_score=40.0, current_mood="tsundere")
    tsun_text = composer._build_acting_direction(tsun_data)
    assert "ツンデレ" in tsun_text or "憎まれ口" in tsun_text

    # 3. 好意期 (affectionate)
    aff_data = AffinityData(character_name="エリス", affinity_score=75.0, trust_score=70.0, current_mood="affectionate")
    aff_text = composer._build_acting_direction(aff_data)
    assert "好意的" in aff_text or "笑顔" in aff_text

    # 4. 盲信・独占・デレ期 (deep_love)
    love_data = AffinityData(character_name="エリス", affinity_score=90.0, dependency_score=85.0, current_mood="deep_love")
    love_text = composer._build_acting_direction(love_data)
    assert "熱烈な好意" in love_text or "密着" in love_text


@pytest.mark.asyncio
async def test_prompt_composer_compose_writing_prompt_with_affinity():
    """ステップ 31: compose_writing_prompt に好感度ディレクションが結合されること"""
    mock_agent = MagicMock()
    mock_prompt_mgr = MagicMock()
    mock_prompt_mgr.build_final_writing_prompt = AsyncMock(return_value="【基本プロンプト】本文を書いてください。")
    mock_agent.prompt_manager = mock_prompt_mgr

    composer = PromptComposer(agent=mock_agent)
    
    aff_data = AffinityData(character_name="シルフィ", affinity_score=80.0, trust_score=80.0, current_mood="affectionate")
    context = {
        "plot": {"detailed_blueprint": "プロット詳細"},
        "affinity_data": [aff_data],
    }

    result = await composer.compose_writing_prompt(book_id=1, ep_num=1, context=context)
    assert "【基本プロンプト】" in result
    assert "【キャラクター演技・好感度ディレクション】" in result
    assert "シルフィ" in result
    assert "affectionate" in result
