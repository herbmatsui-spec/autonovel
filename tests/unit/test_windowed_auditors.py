"""Unit and integration tests for windowed auditors on 8000+ chars drafts (Step 47)."""

import pytest
from unittest.mock import MagicMock
from src.agents.specialists.windowing import NovelSectionExtractor
from src.agents.specialists.reader_hook_auditor import ReaderHookAuditor
from src.agents.specialists.structure_auditor import StructureAuditor
from src.agents.specialists.emotion_curve_auditor import EmotionCurveAuditor
from src.agents.specialists.multimodal_auditor import MultimodalAuditor


@pytest.fixture
def long_novel_8000():
    """Build a realistic 8000-char novel chapter with distinct sections."""
    # Opening (approx 2000 chars)
    opening = (
        "なぜ少女は一人で雨の中に立っていたのか？ 奇妙な違和感が胸を締め付ける。\n"
        + "街の灯りが濡れたアスファルトに反射し、冷たい風が吹き抜けていく。" * 60
        + "\n"
    )

    # Middle part 1 / Sho (approx 2500 chars)
    middle_1 = (
        "探索を続けるうちに、古びた図書館の地下へと足を踏み入れた。" * 100
        + "\n"
    )

    # Middle part 2 / Ten - Climax with illustration scene (approx 2500 chars)
    middle_2 = (
        "深層の祭壇で、白銀の甲冑を纏った騎士エリスが聖剣を抜いた！ 蒼い光が闇を切り裂く。\n"
        + "激しい剣戟の音が響き渡り、火花が夜を焦がした。" * 100
        + "\n"
    )

    # Ending / Ketsu with cliffhanger (approx 2000 chars)
    ending = (
        "戦いは終わったかに見えた。しかし、瓦礫の山が突如として蠢き始めた。" * 80
        + "\n背後から不気味な黒い影が現れた！ 一体どうなるのか！？"
    )

    full_text = opening + middle_1 + middle_2 + ending
    assert len(full_text) >= 8000
    return full_text


def test_section_extractor_on_8000_chars(long_novel_8000):
    extractor = NovelSectionExtractor()

    # Opening test
    op = extractor.extract_opening(long_novel_8000, max_chars=1200)
    assert len(op) <= 1200
    assert "なぜ少女は一人で雨の中に立っていたのか？" in op
    assert op.endswith("。")

    # Ending test
    ed = extractor.extract_ending(long_novel_8000, max_chars=1200)
    assert len(ed) <= 1200
    assert "背後から不気味な黒い影が現れた！ 一体どうなるのか！？" in ed

    # 4-sections test
    sections = extractor.extract_four_sections(long_novel_8000, section_chars=600)
    assert len(sections) == 4
    assert sections[0].name == "ki"
    assert sections[1].name == "sho"
    assert sections[2].name == "ten"
    assert sections[3].name == "ketsu"

    for sec in sections:
        assert len(sec.text) > 0
        assert len(sec.text) <= 800


@pytest.mark.asyncio
async def test_reader_hook_auditor_on_8000_chars(long_novel_8000):
    mock_llm = MagicMock()
    auditor = ReaderHookAuditor(llm=mock_llm)

    captured = {}

    async def mock_judge(prompt, system_prompt):
        captured["prompt"] = prompt
        return 95.0, "Outstanding opening mystery and ending cliffhanger", ["None"], 0.98, "trace", "raw"

    auditor._judge_with_llm = mock_judge
    result = await auditor.audit({"draft_text": long_novel_8000})

    assert result.score == 95.0
    prompt = captured["prompt"]
    # Check both ends in prompt
    assert "なぜ少女は一人で雨の中に立っていたのか？" in prompt
    assert "背後から不気味な黒い影が現れた！ 一体どうなるのか！？" in prompt
    assert f"【総文字数】{len(long_novel_8000)}文字" in prompt


@pytest.mark.asyncio
async def test_structure_auditor_on_8000_chars(long_novel_8000):
    mock_llm = MagicMock()
    auditor = StructureAuditor(llm=mock_llm)

    captured = {}

    async def mock_judge(prompt, system_prompt):
        captured["prompt"] = prompt
        return 89.0, "Good pacing across 8000 words", [], 0.9, "trace", "raw"

    auditor._judge_with_llm = mock_judge
    result = await auditor.audit({
        "draft_text": long_novel_8000,
        "plot_tree": "導入→調査→決戦→余韻",
    })

    assert result.score == 89.0
    prompt = captured["prompt"]
    assert "【起（導入セクション）】" in prompt
    assert "【結（結び・余韻セクション）】" in prompt
    assert "背後から不気味な黒い影が現れた！ 一体どうなるのか！？" in prompt


@pytest.mark.asyncio
async def test_emotion_curve_auditor_on_8000_chars(long_novel_8000):
    mock_llm = MagicMock()
    auditor = EmotionCurveAuditor(llm=mock_llm)

    captured = {}

    async def mock_judge(prompt, system_prompt):
        captured["prompt"] = prompt
        return 91.0, "Great tension curve", [], 0.95, "trace", "raw"

    auditor._judge_with_llm = mock_judge
    result = await auditor.audit({"draft_text": long_novel_8000})

    assert result.score == 91.0
    prompt = captured["prompt"]
    assert "【序盤フェーズ（導入の感情状態）】" in prompt
    assert "【結末フェーズ（カタルシス・感情の解放・余韻）】" in prompt


@pytest.mark.asyncio
async def test_multimodal_auditor_matches_scene_in_8000_chars(long_novel_8000):
    mock_llm = MagicMock()
    auditor = MultimodalAuditor(llm=mock_llm)

    captured = {}

    async def mock_judge(prompt, system_prompt):
        captured["prompt"] = prompt
        return 93.0, "Illustration perfectly matches the deep altar scene", [], 0.92, "trace", "raw"

    auditor._judge_with_llm = mock_judge
    result = await auditor.audit({
        "draft_text": long_novel_8000,
        "illustration_prompts": "白銀の甲冑を纏った騎士エリスが祭壇で聖剣を構えるシーン。蒼い光のエフェクト。",
    })

    assert result.score == 93.0
    prompt = captured["prompt"]
    # The scene is deep inside the draft (around char 4000-6000), not in the first 3000 chars!
    assert "エリスが聖剣を抜いた" in prompt
    assert result.feedback["matched_draft_chars"] <= 3000


def test_reader_hook_fallback_on_8000_chars(long_novel_8000):
    auditor = ReaderHookAuditor()  # No LLM -> fallback
    result = auditor._fallback({"draft_text": long_novel_8000})
    assert result.degraded
    # Score should be high because both opening and ending have strong hooks
    assert result.score >= 35.0
