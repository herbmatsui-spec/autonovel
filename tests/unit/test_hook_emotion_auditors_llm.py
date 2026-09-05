"""Unit tests for LLM-based ReaderHookAuditor and EmotionCurveAuditor (Step 66)."""

import pytest
from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
from src.agents.specialists.emotion_curve_auditor import EmotionCurveAuditor


class DummyLLM:
    def __init__(self, response_text: str):
        self.response_text = response_text

    async def ainvoke(self, prompt, **kwargs):
        class Resp:
            def __init__(self, content):
                self.content = content
        return Resp(self.response_text)


@pytest.mark.asyncio
async def test_reader_hook_with_llm():
    llm_json = '{"score": 85.0, "critique": "冒頭の謎提示が鮮烈で、ラストのクリフハンガーも読者を強く惹きつけます。", "suggestions": ["第2パラグラフのテンポをさらにアップ"]}'
    auditor = ReaderHookAuditor(llm=DummyLLM(llm_json))
    ctx = {"draft_text": "なぜ彼女は死ななければならなかったのか？その謎を追う僕の前に、突如怪しい影が現れた……！"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "reader_hook"
    assert res.score == 85.0
    assert not res.degraded
    assert "クリフハンガー" in res.feedback.get("critique", "")
    assert len(res.suggestions) == 1


@pytest.mark.asyncio
async def test_reader_hook_fallback():
    auditor = ReaderHookAuditor(llm=None)
    ctx = {"draft_text": "なぜ？どうしてこんなことに！……"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "reader_hook"
    assert res.degraded is True
    assert 0.0 <= res.score <= 100.0


@pytest.mark.asyncio
async def test_emotion_curve_with_llm():
    llm_json = '{"score": 90.0, "critique": "絶望的な危機からの劇的なカタルシスが見事に描かれています。", "suggestions": []}'
    auditor = EmotionCurveAuditor(llm=DummyLLM(llm_json))
    ctx = {"draft_text": "絶望の淵で剣を振り上げた。一筋の光が差し込み、勝利の歓喜が仲間たちを包んだ。"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "emotion_curve"
    assert res.score == 90.0
    assert not res.degraded
    assert "カタルシス" in res.feedback.get("critique", "")


@pytest.mark.asyncio
async def test_emotion_curve_fallback():
    auditor = EmotionCurveAuditor(llm=None)
    ctx = {"draft_text": "暗い森の奥で恐怖に怯えていた。\n\nしかし、希望の光が現れて安堵の涙を流した。"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "emotion_curve"
    assert res.degraded is True
    assert 0.0 <= res.score <= 100.0


@pytest.mark.asyncio
async def test_empty_draft_hook_and_emotion():
    h_auditor = ReaderHookAuditor(llm=None)
    e_auditor = EmotionCurveAuditor(llm=None)

    h_res = await h_auditor.safe_audit({"draft_text": ""})
    e_res = await e_auditor.safe_audit({"draft_text": ""})

    assert h_res.score == 0.0
    assert e_res.score == 0.0
