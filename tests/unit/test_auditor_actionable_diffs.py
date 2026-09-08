"""Unit tests for ActionableDiff generation in auditors (Step 58-59)."""

import pytest
from unittest.mock import MagicMock
import json
from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
from src.agents.specialists.consistency_auditor import ConsistencyAuditor
from src.agents.specialists.structure_auditor import StructureAuditor
from src.agents.specialist_auditor_base import ActionableDiff


def test_reader_hook_fallback_generates_actionable_diffs():
    # A draft completely lacking opening hook and ending hook
    plain_draft = "彼は歩いた。街は静かだった。ただそれだけの日だった。" * 50
    auditor = ReaderHookAuditor()  # No LLM -> fallback
    result = auditor._fallback({"draft_text": plain_draft})

    assert result.degraded
    assert len(result.actionable_diffs) >= 1
    for diff in result.actionable_diffs:
        assert isinstance(diff, ActionableDiff)
        assert len(diff.location) > 0
        assert len(diff.original_quote) > 0
        assert len(diff.improved_suggestion) > 0
        assert len(diff.rationale) > 0


def test_consistency_fallback_generates_actionable_diffs_on_contradiction():
    # Draft with contradiction: deceased character acting
    contradiction_draft = "勇者は既に息絶えていた。しかし次の瞬間、勇者は元気に笑って剣を振った。"
    auditor = ConsistencyAuditor()  # No LLM -> fallback
    result = auditor._fallback({
        "draft_text": contradiction_draft,
        "world_bible_snapshot": {
            "characters": [
                {"name": "勇者", "status": "死亡", "description": "第1話で命を落とした"}
            ]
        }
    })

    assert result.degraded
    if result.feedback.get("rule_consistency", 1.0) < 0.5:
        assert len(result.actionable_diffs) >= 1
        assert "矛盾" in result.actionable_diffs[0].rationale


@pytest.mark.asyncio
async def test_structure_auditor_with_llm_actionable_diffs():
    mock_llm = MagicMock()
    mock_llm.ainvoke = MagicMock(return_value=json.dumps({
        "score": 70.0,
        "critique": "中盤の展開が間延びしている。",
        "suggestions": ["展開のテンポアップ"],
        "confidence": 0.9,
        "reasoning": "中盤停滞",
        "actionable_diffs": [
            {
                "location": "承セクション中盤",
                "original_quote": "主人公は店で買い物をして、その後お茶を飲んでぼんやり過ごした。",
                "improved_suggestion": "街の路地で不穏な黒服の集団を目撃し、身を隠しながら追跡を開始した。",
                "rationale": "無目的な日常シーンをプロット進展に繋がるサスペンス展開に置換するため"
            }
        ]
    }, ensure_ascii=False))

    auditor = StructureAuditor(llm=mock_llm)
    result = await auditor.audit({"draft_text": "テストドラフト" * 50})

    assert result.score == 70.0
    assert len(result.actionable_diffs) == 1
    diff = result.actionable_diffs[0]
    assert diff.location == "承セクション中盤"
    assert "不穏な黒服の集団" in diff.improved_suggestion
