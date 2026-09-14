"""
E2E integration test for Opening Booster Pipeline (Episodes 1 to 3).
PLAN 02 - Step 12: 序盤3話の通し生成とクリフハンガー基準達成のE2Eテスト
"""
from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from src.agents.writing.generator import WritingGenerator
from src.models.opening_booster import CliffhangerType


@pytest.mark.asyncio
async def test_opening_booster_pipeline_e2e():
    """第1話〜第3話を連続生成し、全話で80点以上のクリフハンガーを達成していることをE2E検証"""
    episodes_content = {
        1: (
            "「貴様のような無能は我が勇者パーティーに不要だ！今すぐ消え失せろ！」\n"
            "冷酷な追放宣告を受け、アルトは絶望の奈落『黒妖迷宮』の最深部に置き去りにされた。\n"
            "だが死の恐怖の中で、世界の理を書き換える固有権能【神域付与】が覚醒する！\n"
            "…その時、背後の扉が轟音と共に蹴り破られた。「見つけたぞ、裏切り者め」"
        ),
        2: (
            "黒妖迷宮を踏破したアルトは、隣国の辺境領へと足を踏み入れた。\n"
            "そこへ突如襲来したAランク災害巨獣を、アルトは一振りの木の棒に施した神域付与で粉砕する。\n"
            "「あ、ありえない……！ 一撃で竜種を消滅させたというの……！？」\n"
            "目撃した女騎士が呆然と膝を突く中、遠く帝都の元勇者は深刻な魔力枯渇に青ざめていた。"
        ),
        3: (
            "一方その頃、アルトを追放した元勇者パーティーは補給と索敵の崩壊により壊滅寸前に陥っていた。\n"
            "「くそっ、なぜこんな簡単な結界すら維持できないんだ！？」と罵り合う元仲間たち。\n"
            "対してアルトは辺境都市で英雄として迎えられ、莫大な報酬と貴族の爵位を授与される。\n"
            "口元に冷笑を浮かべ、男は静かに呟いた。「そうか、これが貴様らの全力か。……ならば次は、こちらの番だな」"
        ),
    }

    mock_llm = AsyncMock()

    async def mock_generate_text(purpose: str, prompt: str):
        if "第1話" in prompt or "opening_ep01" in prompt:
            return episodes_content[1]
        elif "第2話" in prompt or "opening_ep02" in prompt:
            return episodes_content[2]
        elif "第3話" in prompt or "opening_ep03" in prompt:
            return episodes_content[3]
        return episodes_content[1]

    mock_llm.generate_text.side_effect = mock_generate_text

    generator = WritingGenerator(llm=mock_llm)

    for ep in [1, 2, 3]:
        res = await generator.generate_opening_if_applicable(
            book_id=1,
            ep_num=ep,
            target_word_count=2500,
            inciting_incident="理不尽な追放と虐げ",
            payoff_moment="神域スキルの覚醒とざまぁの開始",
            genre="ハイファンタジー",
            protagonist_name="アルト",
        )

        assert res is not None
        assert res["ep_num"] == ep
        assert len(res["content"]) > 50

        # クリフハンガー品質のE2Eアサート
        cliff = res["cliffhanger"]
        assert cliff.score >= 80.0, f"Episode {ep} cliffhanger score {cliff.score} < 80.0"
        assert cliff.requires_rewrite is False, f"Episode {ep} requested unexpected rewrite"
        assert cliff.hook_type != CliffhangerType.PEACEFUL, f"Episode {ep} had peaceful ending"
        assert cliff.tail_sentence != ""


@pytest.mark.asyncio
async def test_opening_booster_self_healing_rewrite_loop():
    """初回の生成で平穏な終わり方（失格）だった場合、自動リライトによって合格クリフハンガーへ自己修復すること"""
    first_try_peaceful = (
        "アルトは理不尽に追放されたが、新しい街でパン屋を始めた。\n"
        "今日も良い一日だった。主人公は温かいベッドに入り、静かに眠りについた。"
    )
    second_try_crisis = (
        "アルトは理不尽に追放されたが、失意の中で神域付与が覚醒した。\n"
        "…その時、背後の扉が轟音と共に蹴り破られた。「見つけたぞ、裏切り者め」"
    )

    mock_llm = AsyncMock()
    mock_llm.generate_text.side_effect = [first_try_peaceful, second_try_crisis]

    generator = WritingGenerator(llm=mock_llm)

    res = await generator.generate_opening_if_applicable(
        book_id=1,
        ep_num=1,
        target_word_count=2500,
    )

    assert res is not None
    assert mock_llm.generate_text.call_count == 2
    assert res["cliffhanger"].score >= 80.0
    assert res["cliffhanger"].hook_type == CliffhangerType.CRISIS
    assert res["cliffhanger"].requires_rewrite is False
