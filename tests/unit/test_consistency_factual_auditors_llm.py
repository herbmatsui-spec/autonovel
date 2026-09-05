"""Unit tests for Consistency & Factual Specialist Auditors with LLM (Step 64)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.agents.specialists.consistency_auditor import ConsistencyAuditor
from src.agents.specialists.factual_auditor import FactualAuditor


def _make_llm_mock(json_response: str) -> MagicMock:
    """Create an LLM mock that returns the given JSON response for ainvoke/generate/invoke."""
    mock = MagicMock()
    # _judge_with_llm checks ainvoke first, then generate, then invoke
    # Make all three return the JSON response
    async def _ainvoke(*args, **kwargs):
        return json_response
    mock.ainvoke = _ainvoke
    mock.generate = MagicMock(return_value=json_response)
    mock.invoke = MagicMock(return_value=json_response)
    # Also make it callable directly
    mock.__call__ = MagicMock(return_value=json_response)
    return mock


@pytest.mark.asyncio
async def test_consistency_auditor_with_llm_contradiction_detection():
    """Step 64: ConsistencyAuditor が LLM で死亡キャラの再登場などの論理矛盾を検知して低スコアを返すこと."""
    json_resp = """
{
  "score": 35.0,
  "critique": "第1章で戦死したはずのゼノンが何の説明もなく元気に酒場で会話しており、重大な論理矛盾が存在する。",
  "suggestions": ["ゼノンの登場を回想シーンにするか、蘇生の経緯を明記すること"]
}
"""
    mock_llm = _make_llm_mock(json_resp)
    auditor = ConsistencyAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "酒場の扉を開けると、そこにはゼノンが笑って座っていた。「久しぶりだな」と彼は言った。",
        "world_bible_snapshot": {
            "characters": [
                {"name": "ゼノン", "status": "死亡（第1話にて戦死）"},
                {"name": "アルカディア", "status": "生存"},
            ]
        },
    }

    result = await auditor._safe_audit(ctx)
    assert result.specialist_name == "consistency"
    assert result.score == 35.0
    assert result.degraded is False
    assert "戦死" in result.feedback["critique"]
    assert len(result.suggestions) >= 1


@pytest.mark.asyncio
async def test_consistency_auditor_fallback_without_llm():
    """Step 64: LLM未指定時に死生正規表現走査に依存せず安全にルールベースフォールバックすること."""
    auditor = ConsistencyAuditor(llm=None)
    ctx = {
        "draft_text": "アルカディアは王都広場で剣を抜いた。生死をかけた戦いが始まる。",
        "world_bible_snapshot": {
            "characters": [{"name": "アルカディア"}],
            "locations": [{"name": "王都広場"}],
        },
    }

    result = await auditor._safe_audit(ctx)
    assert result.specialist_name == "consistency"
    assert result.degraded is True
    # 「死」と「生」の近接による理不尽な減点ではなく、カバレッジに基づく適切なスコア
    assert result.score >= 50.0


@pytest.mark.asyncio
async def test_factual_auditor_with_llm():
    """Step 64: FactualAuditor が事実関係・時代考証をLLMで評価すること."""
    json_resp = """
{
  "score": 90.0,
  "critique": "中世初期の封建制度および神聖暦の年代記述に誤りはなく、世界観設定に極めて忠実である。",
  "suggestions": ["貨幣単位の記述をより詳細にすると世界観の深みが増す"]
}
"""
    mock_llm = _make_llm_mock(json_resp)
    auditor = FactualAuditor(llm=mock_llm)
    ctx = {
        "draft_text": "神聖暦七四二年、銀貨三枚を支払って馬車を借りた。",
        "world_bible_snapshot": {
            "terms": ["神聖暦", "帝国銀貨"],
        },
    }

    result = await auditor._safe_audit(ctx)
    assert result.specialist_name == "factual"
    assert result.score == 90.0
    assert "中世初期" in result.feedback["critique"]


@pytest.mark.asyncio
async def test_factual_auditor_fallback_modern_terms():
    """Step 64: FactualAuditor のフォールバックで現代語混入が検知されること."""
    auditor = FactualAuditor(llm=None)
    ctx = {
        "draft_text": "騎士はスマホを取り出して時間を確認し、エレベーターに乗った。",
        "world_bible_snapshot": {},
    }

    result = await auditor._safe_audit(ctx)
    assert result.specialist_name == "factual"
    assert result.degraded is True
    # スマホとエレベーターの2語検知で減点
    assert result.score < 60.0
    assert "スマホ" in result.feedback["modern_terms_found"]
