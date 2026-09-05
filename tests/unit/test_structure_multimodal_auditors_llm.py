"""Unit tests for LLM-based StructureAuditor and MultimodalAuditor (Step 67)."""

import pytest
from src.agents.specialists.structure_auditor import StructureAuditor
from src.agents.specialists.multimodal_auditor import MultimodalAuditor


class DummyLLM:
    def __init__(self, response_text: str):
        self.response_text = response_text

    async def ainvoke(self, prompt, **kwargs):
        class Resp:
            def __init__(self, content):
                self.content = content
        return Resp(self.response_text)


@pytest.mark.asyncio
async def test_structure_auditor_with_llm():
    llm_json = '{"score": 87.0, "critique": "起承転結のテンポが良好で、プロットの重要ポイントを漏れなく消化しています。", "suggestions": ["転の部分の緊迫感をさらに高める"]}'
    auditor = StructureAuditor(llm=DummyLLM(llm_json))
    ctx = {
        "draft_text": "城門が開いた。勇者は深呼吸をして足を踏み入れた。罠が発動し、矢が降り注ぐ。彼は盾で防ぎ、奥の玉座へと進んだ。",
        "plot_tree": "城門突入 → 罠の回避 → 玉座への到達",
    }

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "structure"
    assert res.score == 87.0
    assert not res.degraded
    assert "起承転結" in res.feedback.get("critique", "")


@pytest.mark.asyncio
async def test_structure_auditor_fallback():
    auditor = StructureAuditor(llm=None)
    ctx = {
        "draft_text": "城門が開いた。勇者は罠を回避し、玉座へと到達した。",
        "plot_tree": "城門 罠 玉座",
    }

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "structure"
    assert res.degraded is True
    assert 0.0 <= res.score <= 100.0


@pytest.mark.asyncio
async def test_multimodal_auditor_with_llm():
    llm_json = '{"score": 93.0, "critique": "本文の決戦シーンと挿絵指示の構図・雷光のライティングが完璧に一致しています。", "suggestions": []}'
    auditor = MultimodalAuditor(llm=DummyLLM(llm_json))
    ctx = {
        "draft_text": "雨の中、黒衣の剣士が抜刀した。刀身に紫の雷光が走る。",
        "illustration_prompts": "雨の荒野、黒衣の剣士が紫の雷を帯びた剣を構える、シリアスで劇的なライティング",
    }

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "multimodal"
    assert res.score == 93.0
    assert not res.degraded
    assert "雷光" in res.feedback.get("critique", "")


@pytest.mark.asyncio
async def test_multimodal_auditor_fallback():
    auditor = MultimodalAuditor(llm=None)
    ctx = {
        "draft_text": "雨の中、黒衣の剣士が抜刀した。",
        "illustration_prompts": "雨の荒野、黒衣の剣士",
    }

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "multimodal"
    assert res.degraded is True
    assert 0.0 <= res.score <= 100.0


@pytest.mark.asyncio
async def test_multimodal_auditor_no_prompt():
    auditor = MultimodalAuditor(llm=None)
    ctx = {"draft_text": "本文だけが存在する。"}

    res = await auditor.safe_audit(ctx)
    assert res.specialist_name == "multimodal"
    assert res.score == 50.0


@pytest.mark.asyncio
async def test_empty_draft_structure_and_multimodal():
    st_auditor = StructureAuditor(llm=None)
    mm_auditor = MultimodalAuditor(llm=None)

    st_res = await st_auditor.safe_audit({"draft_text": ""})
    mm_res = await mm_auditor.safe_audit({"draft_text": ""})

    assert st_res.score == 0.0
    assert mm_res.score == 0.0
