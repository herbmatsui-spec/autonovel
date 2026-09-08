"""Unit tests for ActionableDiff LLM parsing and specialist integration (Step 55-57)."""

import json
import pytest
from unittest.mock import MagicMock
from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
from src.agents.specialists.consistency_auditor import ConsistencyAuditor
from src.agents.specialist_auditor_base import ActionableDiff


@pytest.mark.asyncio
async def test_judge_with_llm_parses_actionable_diffs():
    mock_llm = MagicMock()
    json_payload = {
        "score": 85.0,
        "critique": "冒頭のフックは強力だが、中盤の描写がやや説明的。",
        "suggestions": ["説明的な地の文を削って五感描写を増やす"],
        "confidence": 0.95,
        "reasoning": "フックとテンポのバランスが良い",
        "actionable_diffs": [
            {
                "location": "冒頭第2段落",
                "original_quote": "彼は昔のことを思い出した。とても悲しかった。",
                "improved_suggestion": "冷たい雨粒が頬を伝い、過去の苦い記憶が胸を締め付けた。",
                "rationale": "説明的な感情語を避け、五感描写で感情を表現するため"
            },
            {
                "location": "章末結末",
                "original_quote": "そして夜が終わった。",
                "improved_suggestion": "闇の奥で、不気味な足音が一つ鳴り響いた……。",
                "rationale": "次章へのクリフハンガーを強化するため"
            }
        ]
    }
    mock_llm.ainvoke = MagicMock(return_value=json.dumps(json_payload, ensure_ascii=False))

    auditor = ReaderHookAuditor(llm=mock_llm)
    result = await auditor.audit({"draft_text": "テストドラフト文章です。冒頭から末尾まで。"})

    assert result.score == 85.0
    assert len(result.actionable_diffs) == 2

    diff1 = result.actionable_diffs[0]
    assert isinstance(diff1, ActionableDiff)
    assert diff1.location == "冒頭第2段落"
    assert "とても悲しかった" in diff1.original_quote
    assert "冷たい雨粒" in diff1.improved_suggestion

    diff2 = result.actionable_diffs[1]
    assert diff2.location == "章末結末"
    assert "不気味な足音" in diff2.improved_suggestion

    # Verify serialization in to_dict()
    res_dict = result.to_dict()
    assert len(res_dict["actionable_diffs"]) == 2
    assert res_dict["actionable_diffs"][0]["location"] == "冒頭第2段落"


@pytest.mark.asyncio
async def test_judge_with_llm_backward_compatible_without_diffs():
    mock_llm = MagicMock()
    # Old LLM output without actionable_diffs
    json_payload = {
        "score": 75.0,
        "critique": "標準的な構成。",
        "suggestions": ["推敲を推奨"],
        "confidence": 0.8,
        "reasoning": "特に問題なし"
    }
    mock_llm.ainvoke = MagicMock(return_value=json.dumps(json_payload, ensure_ascii=False))

    auditor = ConsistencyAuditor(llm=mock_llm)
    result = await auditor.audit({"draft_text": "普通の本文。"})

    assert result.score == 75.0
    assert result.actionable_diffs == []
    res_dict = result.to_dict()
    assert res_dict["actionable_diffs"] == []
