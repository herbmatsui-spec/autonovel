"""
Unit tests for PromptComposer emotion instruction integration.
PLAN 03 - Step 9: 執筆プロンプトへの生々しい感情指示埋め込み検証
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.agents.prompt_composer import PromptComposer


@pytest.mark.asyncio
async def test_prompt_composer_prepends_raw_emotion_instruction():
    """compose_writing_promptがAI感情説明の外科的禁止指示をプロンプト先頭に注入すること"""
    mock_agent = MagicMock()
    mock_pm = MagicMock()
    mock_pm.build_final_writing_prompt = AsyncMock(return_value="[本文生成指示: 第5話の戦闘シーン]")
    mock_agent.prompt_manager = mock_pm

    composer = PromptComposer(agent=mock_agent)
    context = {
        "plot": {"detailed_blueprint": "設計図"},
        "character": {
            "name": "アルト",
            "personality": "熱血",
        },
        "target_word_count": 2500,
    }

    result = await composer.compose_writing_prompt(
        book_id=1,
        ep_num=5,
        context=context,
    )

    # raw_emotion_instruction の重要キーワードが含まれていること
    assert "AI優等生病・感情説明の外科的禁止" in result
    assert "感情の三段論法を完全禁止" in result
    assert "身体的生理反応" in result
    assert "主人公の本音・毒気設定" in result
    assert "[本文生成指示: 第5話の戦闘シーン]" in result
