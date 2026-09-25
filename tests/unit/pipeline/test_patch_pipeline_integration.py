"""
Integration and unit tests for the Patch Pipeline components.
Tests PatchMerger, ParagraphPatchAgent, and FastScreener.
"""

import pytest

from src.models.patch_pdca import ParagraphTarget, PatchRewriteResult
from src.services.audit.fast_screener import FastScreener
from src.services.prose.patch_merger import PatchMerger
from src.agents.writing.paragraph_patch_agent import ParagraphPatchAgent


def test_patch_merger_normal_merge():
    """Verify that PatchMerger correctly replaces targeted paragraphs by index."""
    original_text = (
        "第1段落のテキストです。主人公が歩き始める。\n\n"
        "第2段落のテキストです。天気が悪くなってきた。\n\n"
        "第3段落のテキストです。街の門が見えてきた。"
    )

    patches = [
        PatchRewriteResult(
            index=1,
            patched_text="第2段落の修正テキストです。黒雲が空を覆い、激しい雨が降り始めた。",
            confidence_score=0.95,
        )
    ]

    merger = PatchMerger()
    merged = merger.merge_patches(original_text, patches)

    assert "第1段落のテキストです。" in merged
    assert "第2段落の修正テキストです。黒雲が空を覆い、激しい雨が降り始めた。" in merged
    assert "第3段落のテキストです。" in merged
    assert "天気が悪くなってきた。" not in merged


def test_patch_merger_out_of_bounds():
    """Verify that PatchMerger safely ignores out-of-range paragraph indices."""
    original_text = "段落一つ目。\n\n段落二つ目。"
    patches = [
        PatchRewriteResult(
            index=99,
            patched_text="存在しない段落のパッチ",
            confidence_score=0.5,
        )
    ]
    merger = PatchMerger()
    merged = merger.merge_patches(original_text, patches)
    assert merged == original_text


@pytest.mark.asyncio
async def test_paragraph_patch_agent_rewrite():
    """Verify that ParagraphPatchAgent generates rewrite results with confidence score."""
    agent = ParagraphPatchAgent()
    target = ParagraphTarget(
        index=0,
        original_text="勇者は剣を抜いた。",
        issue_category="emotional_flatness",
        directive="もっと緊張感を込めて描写する",
    )
    context = {
        "prev_paragraph": "魔王が冷たく笑う。",
        "next_paragraph": "静寂が場を支配した。",
    }
    result = await agent.rewrite_paragraph(target, context)
    assert result.index == 0
    assert result.patched_text != ""
    assert result.confidence_score > 0.0


@pytest.mark.asyncio
async def test_fast_screener_heuristics():
    """Verify FastScreener passes quality texts and flags short/empty texts."""
    screener = FastScreener(threshold=60.0)

    # Empty text fails
    score, passed = await screener.screen("")
    assert not passed
    assert score == 0.0

    # Adequate text passes
    sample_text = (
        "朝の冷気が肌を刺す中、アレンは古びた長剣を腰に下げた。\n\n"
        "昨夜の騒動はまだ町に影を落としており、市場の商人たちも小声で囁き合っている。\n\n"
        "「本当に行くのかい？」背後からかけられた少女の声に、彼は無言で振り返り、小さく頷いてみせた。\n\n"
        "果てしない荒野の向こうに、かつての王都が眠っている。運命はすでに動き出していた。"
    )
    score, passed = await screener.screen(sample_text)
    assert passed
    assert score >= 60.0
