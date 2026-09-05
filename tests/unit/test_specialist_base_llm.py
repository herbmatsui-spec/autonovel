"""Unit test for SpecialistAuditor LLM Judge Foundation (Step 63)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.agents.specialist_auditor_base import (
    SpecialistAuditor,
    SpecialistAuditResult,
    LLMUnavailableError,
)


class DummyAuditor(SpecialistAuditor):
    specialist_name = "dummy"

    async def audit(self, ctx: dict) -> SpecialistAuditResult:
        score, critique, suggestions = await self._judge_with_llm("プロンプト")
        return SpecialistAuditResult(
            specialist_name=self.specialist_name,
            score=score,
            feedback={"critique": critique},
            suggestions=suggestions,
        )


@pytest.mark.asyncio
async def test_judge_with_llm_json_parsing():
    """Step 63: 構造化JSON出力からのスコア・講評・改善案パース検証."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = """
```json
{
  "score": 88.5,
  "critique": "伏線の張り方と主人公の心情変化が論理的かつ説得力に富んでいる。",
  "suggestions": ["終盤の台詞回しをより簡潔にするとテンポが向上する"]
}
```
"""
    auditor = DummyAuditor(llm=mock_llm)
    score, critique, suggestions = await auditor._judge_with_llm("テキストを評価せよ")

    assert score == 88.5
    assert "伏線" in critique
    assert len(suggestions) == 1
    assert "台詞回し" in suggestions[0]


@pytest.mark.asyncio
async def test_judge_with_llm_regex_fallback():
    """Step 63: 非JSONテキストからのスコア正規表現フォールバック検証."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "評価スコア: 72.0点。全体の構成は良好だが、後半の展開がやや急ぎ足。"

    auditor = DummyAuditor(llm=mock_llm)
    score, critique, suggestions = await auditor._judge_with_llm("テキストを評価せよ")

    assert score == 72.0
    assert "展開がやや急ぎ足" in critique


@pytest.mark.asyncio
async def test_judge_with_llm_missing_llm_raises_error():
    """Step 63: LLM未設定時にLLMUnavailableErrorが送出されること."""
    auditor = DummyAuditor(llm=None)
    with pytest.raises(LLMUnavailableError):
        await auditor._judge_with_llm("プロンプト")
