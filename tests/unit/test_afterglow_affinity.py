"""
tests/unit/test_afterglow_affinity.py - Phase 4: AfterglowGenerator with Affinity/Mood Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.schemas.ux_schemas import AffinityData
from src.agents.afterglow_generator import AfterglowGenerator


@pytest.mark.asyncio
async def test_afterglow_generator_fallback_by_mood():
    """ステップ 58〜60: moodに応じたフォールバック独白の生成テスト"""
    generator = AfterglowGenerator(llm_gateway=None)

    # 1. 警戒状態 (wary)
    wary_data = AffinityData(character_name="エリス", current_mood="wary")
    res_wary = await generator.generate_monologue("エリス", "戦闘後", affinity_data=wary_data)
    assert res_wary.sentiment_tag == "wary"
    assert "何を企んでいるの" in res_wary.inner_monologue

    # 2. 独占・盲信 (deep_love)
    love_data = AffinityData(character_name="シルフィ", current_mood="deep_love")
    res_love = await generator.generate_monologue("シルフィ", "日常後", affinity_data=love_data)
    assert res_love.sentiment_tag == "deep_love"
    assert "あなたなしの世界" in res_love.inner_monologue


@pytest.mark.asyncio
async def test_afterglow_generator_with_llm_gateway():
    """ステップ 57: LLM呼び出し時に mood 情報が反映されること"""
    mock_gateway = MagicMock()
    mock_gateway.generate_text = AsyncMock(return_value="（……本当に、バカな人。でも……ありがとう）")

    generator = AfterglowGenerator(llm_gateway=mock_gateway)
    aff_data = AffinityData(character_name="ロキシー", current_mood="tsundere")
    
    res = await generator.generate_monologue("ロキシー", "救出後", affinity_data=aff_data)
    assert res.inner_monologue == "（……本当に、バカな人。でも……ありがとう）"
    assert res.sentiment_tag == "tsundere"
