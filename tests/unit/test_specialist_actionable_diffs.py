"""Tests for Part 1: Specialist Anchors & Actionable Diffs (Step 12 / Checkpoint 2)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    ActionableDiff,
    parse_actionable_diffs,
    parse_audit_response_json,
)
from src.agents.specialists.structure_auditor import StructureAuditor
from src.agents.specialists.emotion_curve_auditor import EmotionCurveAuditor
from src.agents.specialists.style_auditor import StyleAuditor
from src.agents.specialists.consistency_auditor import ConsistencyAuditor


def test_parse_actionable_diffs_variations():
    """Test parsing actionable diffs with various key variations and structures."""
    raw_data = [
        {
            "location": "冒頭",
            "original_quote": "暗い部屋だった。",
            "improved_suggestion": "月光すら拒絶する漆黒の闇が部屋を支配していた。",
            "rationale": "情景描写の深化",
        },
        {
            "target": "結末",
            "before": "彼は笑った。",
            "after": "彼は静かに微笑み、胸を撫で下ろした。",
            "reason": "カタルシス付与",
        },
        {
            "section": "中盤",
            "quote": "走った。",
            "rewrite": "息を切らしながら必死に石畳を駆け抜けた。",
            "why": "緊迫感の向上",
        },
    ]
    diffs = parse_actionable_diffs(raw_data)
    assert len(diffs) == 3
    assert diffs[0].location == "冒頭"
    assert diffs[0].original_quote == "暗い部屋だった。"
    assert diffs[1].location == "結末"
    assert diffs[1].improved_suggestion == "彼は静かに微笑み、胸を撫で下ろした。"
    assert diffs[2].location == "中盤"
    assert diffs[2].rationale == "緊迫感の向上"


def test_parse_audit_response_json_markdown_block():
    """Test extracting JSON from markdown code blocks with comments and trailing commas."""
    markdown_response = """
ここから評価講評です。

```json
{
  "score": 82.5,
  "critique": "構成・テンポともに良好です。",
  "suggestions": ["結末の余韻を強化"],
  "confidence": 0.9,
  "reasoning": "起承転結のバランスが良い",
  "actionable_diffs": [
    {
      "location": "結末部",
      "original_quote": "終わった。",
      "improved_suggestion": "すべてが静寂に包まれ、夜が明けた。",
      "rationale": "余韻の付与",
    }
  ],
}
```

以上で審査を終了します。
"""
    score, critique, suggs, conf, reas, diffs = parse_audit_response_json(markdown_response)
    assert score == 82.5
    assert "良好" in critique
    assert suggs == ["結末の余韻を強化"]
    assert conf == 0.9
    assert len(diffs) == 1
    assert diffs[0].location == "結末部"


@pytest.mark.asyncio
async def test_specialist_auditor_anchor_injection():
    """Test that anchor presets are automatically injected into LLM judge prompts."""
    class DummySpecialist(SpecialistAuditor):
        specialist_name = "reader_hook"
        async def audit(self, ctx):
            return SpecialistAuditResult("reader_hook", 80.0)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value='{"score": 85, "critique": "good", "suggestions": [], "confidence": 0.8}')

    auditor = DummySpecialist(llm=mock_llm)
    await auditor._judge_with_llm(prompt="テスト用プロンプトです。")

    call_args = mock_llm.ainvoke.call_args[0][0]
    # reader_hook のアンカー（HIGH/MID/LOW）が含まれていること
    assert "reader_hook" in call_args
    assert "HIGH" in call_args
    assert "MID" in call_args
    assert "LOW" in call_args


@pytest.mark.asyncio
async def test_structure_auditor_fallback_actionable_diffs():
    """Test StructureAuditor generates Kishotenketsu ActionableDiff in fallback."""
    auditor = StructureAuditor(llm=None)
    ctx = {
        "draft_text": "短い文章。主人公は歩いた。終わり。",
        "plot_tree": "起: 平穏な日常 → 承: 突然の危機と謎の敵 → 転: 最大の戦いと真実の発覚 → 結: 勝利と日常への帰還",
    }
    result = await auditor.safe_audit(ctx)
    assert result.degraded is True
    assert len(result.actionable_diffs) > 0
    # 起承転結のいずれかのフェーズが指摘されていること
    assert any("起" in d.location or "承" in d.location or "転" in d.location or "結" in d.location for d in result.actionable_diffs)


@pytest.mark.asyncio
async def test_emotion_curve_auditor_fallback_actionable_diffs():
    """Test EmotionCurveAuditor generates catharsis/amplitude ActionableDiff in fallback."""
    auditor = EmotionCurveAuditor(llm=None)
    # 起伏もカタルシス語もない平坦な文章
    flat_draft = "彼は朝起きてパンを食べた。外は曇りだった。机に向かって本を開いた。時計の針が進んでいた。夜になりベッドに入った。" * 3
    ctx = {"draft_text": flat_draft}
    result = await auditor.safe_audit(ctx)
    assert result.degraded is True
    assert len(result.actionable_diffs) > 0
    assert any("中盤" in d.location or "結末" in d.location for d in result.actionable_diffs)


@pytest.mark.asyncio
async def test_style_and_consistency_auditors_actionable_diffs():
    """Test StyleAuditor and ConsistencyAuditor actionable diff generation."""
    # Style: 敬体・常体混在
    style_auditor = StyleAuditor(llm=None)
    mixed_style_draft = "彼は歩き始めた。風が強かった。しかし私は驚きました。空が急に暗くなった。"
    res_style = await style_auditor.safe_audit({"draft_text": mixed_style_draft})
    assert res_style.degraded is True
    assert len(res_style.actionable_diffs) > 0
    assert any("語尾" in d.location for d in res_style.actionable_diffs)

    # Consistency: 死亡キャラ登場
    consistency_auditor = ConsistencyAuditor(llm=None)
    inconsistent_draft = "街の酒場に行くと、ルークが酒を飲んでいた。「久しぶりだな」と彼は言った。"
    bible = {
        "characters": [
            {"name": "ルーク", "status": "死亡（第1章で戦死）"},
        ]
    }
    res_consistency = await consistency_auditor.safe_audit({
        "draft_text": inconsistent_draft,
        "world_bible_snapshot": bible,
    })
    assert res_consistency.degraded is True
    assert len(res_consistency.actionable_diffs) > 0
    assert any("ルーク" in d.location or "ルーク" in d.original_quote for d in res_consistency.actionable_diffs)
