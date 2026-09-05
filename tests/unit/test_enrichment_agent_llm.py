"""Unit tests for EnrichmentAgent with LLM-based Sensory Expansion and Token Budget (Step 61)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.orchestrator import AgentContext, AgentName


@pytest.mark.asyncio
async def test_enrichment_agent_sensory_with_llm():
    """Step 61: LLMを用いたShow, Don't Tell推敲とメタデータの検証."""
    mock_llm = MagicMock()
    # LLMが五感を用いた自然な地の文を返すモック
    mock_llm.generate.return_value = "喉の奥が苦く渇き、握りしめた拳の指先にじわりと冷や汗が滲んだ。"

    agent = EnrichmentAgent(llm=mock_llm)
    # config で sensory_expansion を有効化
    agent._config["enabled"] = True
    agent._config["sensory_expansion"] = {"enabled": True}
    agent._config["trivia_insertion"] = {"enabled": False}
    agent._config["citation_attachment"] = {"enabled": False}
    agent._config["multimedia_scenarios"] = {"enabled": False}

    drafted_text = "彼は怒りに震えた。そして剣を抜いた。"
    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={
            "drafted_text": drafted_text,
            "writing_context": {"pov": "三人称", "scene_context": "雨の王都広場"},
        },
    )

    result = await agent.execute(ctx)
    assert result.error is None
    assert result.next_agent == AgentName.AUDIT

    enriched_text = result.artifacts["enriched_text"]
    metadata = result.artifacts["enrichment_metadata"]

    # LLMが生成した五感表現に置き換わっていること
    assert "冷や汗が滲んだ" in enriched_text
    # デバッグ風タグが本文に含まれないこと
    assert "[visual]" not in enriched_text
    assert "[tactile]" not in enriched_text

    # メタデータが収集されていること
    assert len(metadata["sensory"]) >= 1
    sensory_meta = metadata["sensory"][0]
    assert "怒り" in sensory_meta["original_phrase"]
    assert "冷や汗が滲んだ" in sensory_meta["expanded_text"]



@pytest.mark.asyncio
async def test_enrichment_agent_trivia_budget_compliance():
    """Step 61: トリビア挿入におけるトークン予算遵守と品質維持の検証."""
    agent = EnrichmentAgent()
    agent._config["enabled"] = True
    agent._config["trivia_insertion"] = {
        "enabled": True,
        "max_insertions_per_chapter": 5,
        "relevance_threshold": 0.5,
    }
    agent._config["token_budget"] = {
        "max_enrichment_tokens": 100,  # 厳格な低予算 (約80文字のトリビア枠)
    }

    # 大量のトリビア候補（合計文字数が予算を大幅に超過）
    candidates = [
        {"fact": "王都アルカディアはかつて竜の寝床であったとされる。" * 2, "entity": "王都", "source_type": "world_bible"},
        {"fact": "第二のトリビア: 古代文字の記録。" * 2, "entity": "王都", "source_type": "world_bible"},
        {"fact": "第三のトリビア: 禁忌の秘薬。" * 2, "entity": "王都", "source_type": "world_bible"},
    ]

    mock_rag = MagicMock()
    mock_rag.query_trivia_candidates = AsyncMock(return_value=candidates)
    mock_repo = MagicMock()

    agent.rag_service = mock_rag
    agent.repo = mock_repo
    # スコアリングと書き換えをモック
    agent._score_trivia_relevance = MagicMock(return_value=0.9)
    agent._rewrite_trivia_for_context = AsyncMock(side_effect=lambda fact, s, p, e: f"（※{fact}）")

    text = "主人公は王都を歩いていた。街は賑わっていた。"
    enriched, meta = await agent._enrich_with_trivia(text, {"location": "王都"})

    # トークン予算上限により、候補3件のうち下位の候補が安全に切り捨てられていること
    assert len(meta) < len(candidates)
    assert len(meta) >= 1
