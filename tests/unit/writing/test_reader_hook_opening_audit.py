"""
Unit tests for ReaderHookAuditor opening episodes cliffhanger enforcement.
PLAN 02 - Step 11: 監査専門エージェント連携検証
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock
import pytest

from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
from src.core.llm.types import LLMResponse


@pytest.mark.asyncio
async def test_reader_hook_auditor_rejects_peaceful_ending_for_ep01():
    """第1話で平穏な終わり方の原稿はクリフハンガー失格となり低スコアと改善指示が出されること"""
    peaceful_draft = (
        "勇者パーティーを理不尽に追放されたアルト。\n"
        "しかし彼は新天地を見つけ、美味しいご飯を食べた。\n"
        "今日も良い一日だった。主人公は温かいベッドに入り、静かに眠りについた。"
    )

    mock_llm = AsyncMock()
    # LLMが仮に高得点を返そうとしても、序盤話数ルールによりクリフハンガー不合格判定で減点される
    mock_resp = {
        "score": 85.0,
        "critique": "日常描写が丁寧です",
        "suggestions": [],
        "confidence": 0.9,
        "reasoning": "特に問題なし",
    }
    mock_llm.agenerate.return_value = LLMResponse(
        content=f"```json\n{json.dumps(mock_resp, ensure_ascii=False)}\n```",
        model="mock",
    )

    auditor = ReaderHookAuditor(llm=mock_llm)
    result = await auditor.audit({
        "draft_text": peaceful_draft,
        "ep_num": 1,
    })

    # スコアが45点以下に抑制されること
    assert result.score <= 45.0
    # 離脱防止のクリフハンガー改善指示が含まれていること
    assert any("第1話 離脱防止" in s for s in result.suggestions)
    assert "opening_cliffhanger" in result.feedback
    assert result.feedback["opening_cliffhanger"]["hook_type"] == "peaceful"


@pytest.mark.asyncio
async def test_reader_hook_auditor_passes_crisis_ending_for_ep01():
    """第1話で危機的クリフハンガーの原稿は高スコアで合格すること"""
    crisis_draft = (
        "「お前は追放だ！」勇者に罵倒され、迷宮の底に捨てられたアルト。\n"
        "だがその時、眠っていた神スキルが覚醒した。\n"
        "…その時、背後の扉が轟音と共に蹴り破られた。「見つけたぞ、裏切り者め」"
    )

    mock_llm = AsyncMock()
    mock_resp = {
        "score": 90.0,
        "critique": "引きが強いです",
        "suggestions": [],
        "confidence": 0.95,
        "reasoning": "緊迫感あり",
    }
    mock_llm.agenerate.return_value = LLMResponse(
        content=f"```json\n{json.dumps(mock_resp, ensure_ascii=False)}\n```",
        model="mock",
    )

    auditor = ReaderHookAuditor(llm=mock_llm)
    result = await auditor.audit({
        "draft_text": crisis_draft,
        "ep_num": 1,
    })

    assert result.score >= 80.0
    assert not any("第1話 離脱防止" in s for s in result.suggestions)
    assert result.feedback["opening_cliffhanger"]["hook_type"] == "crisis"
