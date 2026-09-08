"""Unit tests for StructureAuditor and EmotionCurveAuditor windowing (Step 43-45)."""

import pytest
from unittest.mock import MagicMock
from src.agents.specialists.structure_auditor import StructureAuditor
from src.agents.specialists.emotion_curve_auditor import EmotionCurveAuditor


@pytest.mark.asyncio
async def test_structure_auditor_windowing_long_draft():
    # Construct 6000+ chars draft with 4 phases
    ki = "平和な村に予兆が現れる。" * 120
    sho = "旅に出た主人公は試練に遭遇する。" * 120
    ten = "最大の敵と対峙し絶体絶命の危機。" * 120
    ketsu = "勝利を収め、新たな希望が灯る。" * 120
    long_draft = ki + "\n" + sho + "\n" + ten + "\n" + ketsu

    assert len(long_draft) > 5000

    mock_llm = MagicMock()
    auditor = StructureAuditor(llm=mock_llm)

    captured_prompt = {}

    async def mock_judge(prompt, system_prompt):
        captured_prompt["prompt"] = prompt
        return 92.0, "Well structured Kishotenketsu", ["Maintain current pacing"], 0.9, "trace", "raw"

    auditor._judge_with_llm = mock_judge

    result = await auditor.audit({
        "draft_text": long_draft,
        "plot_tree": "村の平和→旅立ちと試練→決戦→勝利と帰還",
    })

    assert result.score == 92.0
    assert not result.degraded
    assert "prompt" in captured_prompt
    prompt_text = captured_prompt["prompt"]

    # Verify that all 4 sections are represented in the prompt
    assert "【起（導入セクション）】" in prompt_text
    assert "【承（展開セクション）】" in prompt_text
    assert "【転（山場・転換セクション）】" in prompt_text
    assert "【結（結び・余韻セクション）】" in prompt_text
    assert "平和な村に予兆が現れる。" in prompt_text
    assert "新たな希望が灯る。" in prompt_text
    assert f"【総文字数】{len(long_draft)}文字" in prompt_text
    assert result.feedback["total_chars"] == len(long_draft)
    assert len(result.feedback["sections_extracted"]) == 4


@pytest.mark.asyncio
async def test_emotion_curve_auditor_windowing_long_draft():
    ki = "穏やかな日常から始まる。" * 120
    sho = "不安と緊張が徐々に高まっていく。" * 120
    ten = "怒りと恐怖が最高潮に達する！" * 120
    ketsu = "深い安堵とカタルシスが訪れた。" * 120
    long_draft = ki + "\n" + sho + "\n" + ten + "\n" + ketsu

    assert len(long_draft) > 5000

    mock_llm = MagicMock()
    auditor = EmotionCurveAuditor(llm=mock_llm)

    captured_prompt = {}

    async def mock_judge(prompt, system_prompt):
        captured_prompt["prompt"] = prompt
        return 90.0, "Excellent emotional catharsis at ending", ["Great balance"], 0.95, "trace", "raw"

    auditor._judge_with_llm = mock_judge

    result = await auditor.audit({"draft_text": long_draft})

    assert result.score == 90.0
    assert not result.degraded
    assert "prompt" in captured_prompt
    prompt_text = captured_prompt["prompt"]

    # Verify all phases and ending catharsis
    assert "【序盤フェーズ（導入の感情状態）】" in prompt_text
    assert "【中盤フェーズ（葛藤・緊張の高まり）】" in prompt_text
    assert "【山場フェーズ（最大の感情的クライマックス）】" in prompt_text
    assert "【結末フェーズ（カタルシス・感情の解放・余韻）】" in prompt_text
    assert "深い安堵とカタルシスが訪れた。" in prompt_text
    assert f"【総文字数】{len(long_draft)}文字" in prompt_text
    assert result.feedback["total_chars"] == len(long_draft)
