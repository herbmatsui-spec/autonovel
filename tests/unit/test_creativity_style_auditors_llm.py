"""Unit tests for LLM-based CreativityAuditor and StyleAuditor (Step 65)."""

import pytest
from src.agents.specialists.creativity_auditor import CreativityAuditor
from src.agents.specialists.style_auditor import StyleAuditor


class DummyLLM:
    def __init__(self, response_text: str):
        self.response_text = response_text

    async def ainvoke(self, prompt, **kwargs):
        class Resp:
            def __init__(self, content):
                self.content = content
        return Resp(self.response_text)


@pytest.mark.asyncio
async def test_creativity_auditor_with_llm():
    llm_json = '```json\n{"score": 88.5, "critique": "独創的で鮮烈な比喩表現が多数見られます。", "suggestions": ["後半の語彙をさらに豊かに"]}\n```'
    auditor = CreativityAuditor(llm=DummyLLM(llm_json))
    ctx = {"draft_text": "夜の帳が降りる頃、街のネオンは水銀のように冷たく光っていた。"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "creativity"
    assert res.score == 88.5
    assert not res.degraded
    assert "独創的" in res.feedback.get("critique", "")
    assert len(res.suggestions) == 1


@pytest.mark.asyncio
async def test_creativity_auditor_fallback():
    auditor = CreativityAuditor(llm=None)
    ctx = {"draft_text": "彼は歩いた。彼は立ち止まった。そして彼は空を見上げた。"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "creativity"
    assert res.degraded is True
    assert 0.0 <= res.score <= 100.0


@pytest.mark.asyncio
async def test_style_auditor_with_llm():
    llm_json = '{"score": 92.0, "critique": "格調高い常体で統一されており、ハードボイルドな世界観と完全に一致しています。", "suggestions": []}'
    auditor = StyleAuditor(llm=DummyLLM(llm_json))
    ctx = {
        "draft_text": "冷たい雨がトレンチコートを濡らす。俺はタバコに火をつけた。",
        "style_dna": {"tone": "hardboiled", "person": "first_person"},
    }

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "style"
    assert res.score == 92.0
    assert not res.degraded
    assert "ハードボイルド" in res.feedback.get("critique", "")


@pytest.mark.asyncio
async def test_style_auditor_fallback():
    auditor = StyleAuditor(llm=None)
    ctx = {"draft_text": "私は本を読みます。とても面白い本でした。明日も読みます。"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "style"
    assert res.degraded is True
    assert 0.0 <= res.score <= 100.0


@pytest.mark.asyncio
async def test_empty_draft_handling():
    c_auditor = CreativityAuditor(llm=None)
    s_auditor = StyleAuditor(llm=None)

    c_res = await c_auditor.safe_audit({"draft_text": ""})
    s_res = await s_auditor.safe_audit({"draft_text": ""})

    assert c_res.score == 0.0
    assert s_res.score == 0.0
