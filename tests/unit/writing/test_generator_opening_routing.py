"""
Unit tests for WritingGenerator opening booster routing.
PLAN 02 - Step 10: WritingGeneratorへのルーティング組み込み検証
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest

from src.agents.writing.generator import WritingGenerator


@pytest.mark.asyncio
async def test_writing_generator_routes_episodes_1_to_3():
    """第1話〜第3話はOpeningBoosterAgentへ委譲されることを検証"""
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "「追放だ！」…その時、背後の扉が轟音と共に蹴り破られた。「見つけたぞ」"

    gen = WritingGenerator(llm=mock_llm)

    for ep in [1, 2, 3]:
        res = await gen.generate_opening_if_applicable(
            book_id=1,
            ep_num=ep,
            target_word_count=2500,
            inciting_incident="理不尽な追放",
            payoff_moment="スキルの覚醒",
        )
        assert res is not None
        assert res["ep_num"] == ep
        assert res["content"] != ""
        assert "cliffhanger" in res
        assert res["cliffhanger"].score >= 80.0


@pytest.mark.asyncio
async def test_writing_generator_ignores_episode_4_and_above():
    """第4話以降はOpeningBoosterAgentがバイパスされNoneを返すことを検証"""
    mock_llm = AsyncMock()
    gen = WritingGenerator(llm=mock_llm)

    for ep in [4, 5, 10]:
        res = await gen.generate_opening_if_applicable(
            book_id=1,
            ep_num=ep,
            target_word_count=2500,
        )
        assert res is None
