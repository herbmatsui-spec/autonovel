"""Unit tests for ReaderHookAuditor windowing integration (Step 40-42)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor


@pytest.mark.asyncio
async def test_reader_hook_auditor_windowing_long_draft():
    # Construct a draft longer than 4000 characters (e.g. 6000 chars)
    # Opening has a clear hook, middle is mundane, ending has a cliffhanger.
    opening_part = "なぜ扉が開いていたのか？ そこに誰かが立っていた。\n" + "平穏な日常が続いていた。" * 50
    middle_filler = "日々の仕事や雑用をこなす時間が流れた。" * 300
    ending_part = "足元が突然崩れ落ちた！ 奈落の底から不気味な叫び声が聞こえた……。"
    long_draft = opening_part + middle_filler + ending_part

    assert len(long_draft) > 5000

    mock_llm = MagicMock()
    auditor = ReaderHookAuditor(llm=mock_llm)

    # Intercept _judge_with_llm
    captured_prompt = {}

    async def mock_judge(prompt, system_prompt):
        captured_prompt["prompt"] = prompt
        captured_prompt["system_prompt"] = system_prompt
        return 88.0, "Great hook and cliffhanger", ["Keep up the tension"], 0.95, "trace", "raw"

    auditor._judge_with_llm = mock_judge

    result = await auditor.audit({"draft_text": long_draft})

    assert result.score == 88.0
    assert not result.degraded
    assert "prompt" in captured_prompt

    prompt_text = captured_prompt["prompt"]
    # Verify that BOTH opening hook and ending cliffhanger are present in the prompt
    assert "なぜ扉が開いていたのか？" in prompt_text
    assert "奈落の底から不気味な叫び声が聞こえた……。" in prompt_text
    assert f"【総文字数】{len(long_draft)}文字" in prompt_text
    assert "【冒頭セクション（つかみ・オープニングフック）】" in prompt_text
    assert "【末尾セクション（クリフハンガー・次回への引き）】" in prompt_text


def test_reader_hook_auditor_fallback_long_draft():
    # Verify fallback on long draft uses sentence-snapped opening and ending
    opening_part = "なぜ扉が開いていたのか？ " + "日常の風景が広がる。" * 20
    middle_filler = "日常が続く。" * 200
    ending_part = "何かが背後に現れた！ どうなるのか？"
    long_draft = opening_part + middle_filler + ending_part

    auditor = ReaderHookAuditor()  # No LLM -> fallback
    result = auditor._fallback({"draft_text": long_draft})

    assert result.specialist_name == "reader_hook"
    assert result.score > 0
    assert result.feedback["opening_chars"] > 0
    assert result.feedback["ending_chars"] > 0
