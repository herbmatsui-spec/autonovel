# tests/unit/test_trivia_rewrite.py
"""Unit tests for Step 1-9: Trivia Inline Rewriting and Context Integration."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agents.enrichment_agent import EnrichmentAgent


@pytest.mark.asyncio
async def test_trivia_rewrite_fallback_when_no_llm():
    """LLMが未設定の場合、元のトリビアが安全にフォールバック返却されること (Step 3/4)"""
    agent = EnrichmentAgent(llm=None)
    result = await agent._rewrite_trivia_for_context(
        trivia_fact="王都はかつて湖の底だった。",
        surrounding_text="静かな王都の広場だった。",
        pov="third_person",
        entity="王都",
    )
    assert result == "王都はかつて湖の底だった。"


@pytest.mark.asyncio
async def test_trivia_rewrite_with_mock_llm():
    """LLMが設定されている場合、自然なリライト文が返ること (Step 3)"""
    mock_llm = MagicMock()
    async def fake_ainvoke(p):
        return "かつて湖の底に沈んでいたとされる王都の石畳には、古代の波紋が刻まれていた。"
    mock_llm.ainvoke = fake_ainvoke

    agent = EnrichmentAgent(llm=mock_llm)
    result = await agent._rewrite_trivia_for_context(
        trivia_fact="王都はかつて湖の底だった。",
        surrounding_text="静かな王都の広場だった。",
        pov="third_person",
        entity="王都",
    )
    assert "古代の波紋が刻まれていた" in result


@pytest.mark.asyncio
async def test_trivia_rewrite_timeout_protection():
    """LLMがタイムアウトした場合、元のトリビアがフォールバックされること (Step 4)"""
    import asyncio
    slow_llm = MagicMock()
    async def slow_call(p):
        await asyncio.sleep(5.0)
        return "遅延した回答"
    slow_llm.ainvoke = slow_call

    agent = EnrichmentAgent(llm=slow_llm)
    result = await agent._rewrite_trivia_for_context(
        trivia_fact="秘密の古文書が存在する。",
        surrounding_text="書庫の中は埃っぽかった。",
        pov="third_person",
        entity="古文書",
    )
    assert result == "秘密の古文書が存在する。"


def test_trivia_insertion_dialogue_guard():
    """セリフ「」の途中に挿入インデックスが指定されないこと (Step 5)"""
    agent = EnrichmentAgent()
    text = "「そんな馬鹿な！ 俺は信じないぞ！」と叫び、少年は駆け出した。"
    points = agent._find_insertion_points(text, max_points=2)
    for p in points:
        assert not agent._is_inside_dialogue(text, p), f"Point {p} is inside dialogue!"


def test_trivia_pov_tone_adjustment():
    """一人称指定時に語尾が自然に軟化・補正されること (Step 6)"""
    agent = EnrichmentAgent()
    adjusted = agent._adjust_pov_tone("それは古代の失われた技術であった。", "first_person")
    assert adjusted == "それは古代の失われた技術だった。"

    adjusted_rumor = agent._adjust_pov_tone("王は病に伏せっているとされている。", "first_person")
    assert adjusted_rumor == "王は病に伏せっていると聞いたことがある。"


@pytest.mark.asyncio
async def test_trivia_token_budget_and_metadata_diff():
    """トークン予算上限の遵守とBefore/Afterメタデータの完全記録 (Step 8 & 9)"""
    mock_llm = MagicMock()
    async def fake_ainvoke(p):
        return "聖なる白銀の光を放つ伝説の剣。"
    mock_llm.ainvoke = fake_ainvoke

    agent = EnrichmentAgent(llm=mock_llm)
    mock_rag = MagicMock()
    async def fake_query(*args, **kwargs):
        return [
            {"fact": f"聖剣の歴史その{i}", "source_type": "world_bible", "entity": "聖剣"}
            for i in range(8)
        ]
    mock_rag.query_trivia_candidates = fake_query
    agent.rag_service = mock_rag
    agent.repo = MagicMock()

    writing_context = {"characters": ["アレン"], "location": "神殿", "key_items": ["聖剣"], "pov": "third_person"}
    text = "静かな神殿で聖剣が光った。\n\nアレンは聖剣を握りしめた。\n\n風が吹き抜けた。"
    enriched_text, meta = await agent._enrich_with_trivia(text, writing_context)

    assert len(meta) >= 1
    assert len(meta) <= 5
    for m in meta:
        assert m["original"].startswith("聖剣の歴史その")
        assert "聖なる白銀の光" in m["enriched"]
        assert m["tokens"] > 0
        assert m["entity"] == "聖剣"
