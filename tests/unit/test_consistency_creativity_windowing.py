"""Unit tests for ConsistencyAuditor and CreativityAuditor windowing (Step 49-51)."""

import pytest
from unittest.mock import MagicMock
from src.agents.specialists.consistency_auditor import ConsistencyAuditor
from src.agents.specialists.creativity_auditor import CreativityAuditor


@pytest.mark.asyncio
async def test_consistency_auditor_windowing_with_bible_keywords():
    # Construct 6000+ chars draft where important character appears in the middle/late part
    intro = "静かな森の中を誰もいないまま歩いた。" * 150 + "\n"
    target_scene = "古代遺跡の奥で、賢者アルトリウスが秘伝の魔導書を開いた。\n" + "魔力の波動が渦を巻く。" * 100 + "\n"
    outro = "風が吹き抜けて夜が明けた。" * 150

    long_draft = intro + target_scene + outro
    assert len(long_draft) > 5000

    mock_llm = MagicMock()
    auditor = ConsistencyAuditor(llm=mock_llm)

    captured = {}

    async def mock_judge(prompt, system_prompt):
        captured["prompt"] = prompt
        return 90.0, "Consistent with world bible", [], 0.9, "trace", "raw"

    auditor._judge_with_llm = mock_judge

    result = await auditor.audit({
        "draft_text": long_draft,
        "world_bible_snapshot": {
            "characters": [{"name": "アルトリウス", "role": "賢者"}],
            "lore": "古代遺跡の魔導書",
        },
    })

    assert result.score == 90.0
    prompt = captured["prompt"]
    # Verify that the target scene deep in the draft is extracted and included in prompt
    assert "賢者アルトリウス" in prompt
    assert result.feedback["total_chars"] == len(long_draft)
    assert result.feedback["audited_chars"] <= 3500


@pytest.mark.asyncio
async def test_creativity_auditor_windowing_sampling():
    # Construct 6000+ chars draft with creative metaphors spread across sections
    ki = "月光が銀色のナイフのように夜を引き裂いた。" + "日常の風景が続く。" * 200 + "\n"
    sho = "時間の歯車が軋むような重苦しい沈黙。" + "調査が続く。" * 200 + "\n"
    ten = "星屑の海に身を投じるような忘我の疾走。" + "戦闘が続く。" * 200 + "\n"
    ketsu = "魂の底に沈む静謐な泉のような安らぎ。" + "余韻が続く。" * 200

    long_draft = ki + sho + ten + ketsu
    assert len(long_draft) > 5000

    mock_llm = MagicMock()
    auditor = CreativityAuditor(llm=mock_llm)

    captured = {}

    async def mock_judge(prompt, system_prompt):
        captured["prompt"] = prompt
        return 88.0, "Rich metaphors throughout the chapter", [], 0.9, "trace", "raw"

    auditor._judge_with_llm = mock_judge

    result = await auditor.audit({"draft_text": long_draft})

    assert result.score == 88.0
    prompt = captured["prompt"]
    # Verify sections sampled from throughout the text are included
    assert "KIセクション" in prompt
    assert "KETSUセクション" in prompt
    assert f"【総文字数】{len(long_draft)}文字" in prompt
    assert result.feedback["total_chars"] == len(long_draft)
