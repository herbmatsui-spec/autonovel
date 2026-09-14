"""
Unit tests for OpeningBoosterAgent.
PLAN 02 - Step 5: 序盤特化エージェント単体テスト
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest

from src.config.opening_rules import OPENING_EPISODE_TARGETS, OPENING_FORBIDDEN_RULES
from src.models.opening_booster import CliffhangerType, OpeningEpisodeConfig
from src.agents.writing.opening_booster import OpeningBoosterAgent


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    # 危機的なクリフハンガーで終わる第1話のダミー本文
    llm.generate_text.return_value = (
        "「お前はクビだ、役立たずめ！」\n"
        "勇者の罵声と共に、アルトは追放された。\n"
        "だが最果ての地で、未知なる【神域付与】が覚醒する。\n"
        "…その時、背後の扉が轟音と共に蹴り破られた。「見つけたぞ、裏切り者め」"
    )
    return llm


@pytest.mark.asyncio
async def test_build_opening_prompt_includes_forbidden_rules(mock_llm):
    """第1話のプロンプトに世界観説明禁止等の厳格ルールが含まれているか検証"""
    agent = OpeningBoosterAgent(llm=mock_llm)
    config = OpeningEpisodeConfig(
        ep_num=1,
        target_word_count=2500,
        inciting_incident="勇者パーティーからの理不尽な追放",
        payoff_moment="神域スキルの覚醒",
    )
    prompt = await agent.build_prompt(
        config=config,
        protagonist_name="アルト",
        genre="異世界ファンタジー",
    )

    # 4つの禁止ルールがすべて含まれていることを検証
    for rule in OPENING_FORBIDDEN_RULES:
        assert rule in prompt, f"Rule not found in prompt: {rule}"

    # 第1話ターゲット指示が含まれていることを検証
    assert OPENING_EPISODE_TARGETS[1] in prompt


@pytest.mark.asyncio
async def test_build_opening_prompt_targets_different_episodes(mock_llm):
    """第1話〜第3話でそれぞれ異なるターゲット指示が反映されるか検証"""
    agent = OpeningBoosterAgent(llm=mock_llm)

    for ep in [1, 2, 3]:
        config = OpeningEpisodeConfig(
            ep_num=ep,
            target_word_count=2500,
            inciting_incident=f"第{ep}話の事件",
            payoff_moment=f"第{ep}話の山場",
        )
        prompt = await agent.build_prompt(
            config=config,
            protagonist_name="アルト",
            genre="異世界ファンタジー",
        )
        assert OPENING_EPISODE_TARGETS[ep] in prompt


@pytest.mark.asyncio
async def test_generate_opening_episode_evaluates_cliffhanger(mock_llm):
    """序盤話数の生成結果に対してクリフハンガー評価が自動実行され、合格判定されるか検証"""
    agent = OpeningBoosterAgent(llm=mock_llm)
    config = OpeningEpisodeConfig(
        ep_num=1,
        target_word_count=2500,
        inciting_incident="理不尽な追放",
        payoff_moment="スキルの覚醒",
    )

    result = await agent.generate_opening_episode(
        config=config,
        protagonist_name="アルト",
        genre="異世界ファンタジー",
    )

    assert result["content"] != ""
    assert "cliffhanger" in result
    evaluation = result["cliffhanger"]
    assert evaluation.hook_type == CliffhangerType.CRISIS
    assert evaluation.score >= 80.0
    assert evaluation.requires_rewrite is False
