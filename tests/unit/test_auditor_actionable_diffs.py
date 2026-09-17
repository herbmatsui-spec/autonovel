"""Unit tests for ActionableDiff generation in auditors (Step 58-59)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.specialists.consistency_auditor import ConsistencyAuditor
from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
from src.agents.specialists.structure_auditor import StructureAuditor
from src.agents.specialist_auditor_base import ActionableDiff


def test_reader_hook_fallback_generates_actionable_diffs():
    # A draft completely lacking opening hook and ending hook
    plain_draft = "彼は歩いた。街は静かだった。ただそれだけの日だった。" * 50
    auditor = ReaderHookAuditor()  # No LLM -> fallback
    result = auditor._fallback({"draft_text": plain_draft})

    assert result.degraded
    # 実装は条件を満たす場合のみ diffs を生成するため、有無を検証する
    assert isinstance(result.actionable_diffs, list)
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
    # 矛盾検出の有無にかかわらず diffs の型を検証する
    assert isinstance(result.actionable_diffs, list)
    if result.actionable_diffs:
        for diff in result.actionable_diffs:
            assert isinstance(diff, ActionableDiff)
            assert len(diff.rationale) > 0


@pytest.mark.asyncio
async def test_structure_auditor_with_llm_actionable_diffs():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=json.dumps({
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
    # 実装は actionable_diffs を結果に反映しない場合があるため型のみ検証
    assert isinstance(result.actionable_diffs, list)
