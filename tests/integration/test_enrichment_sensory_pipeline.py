"""Integration tests for sensory expansion pipeline with EnrichmentAgent (Part 2, Step 23)."""
import pytest
from unittest.mock import MagicMock
from src.agents.orchestrator import AgentContext, AgentName
from src.agents.enrichment_agent import EnrichmentAgent


@pytest.mark.asyncio
async def test_enrichment_agent_sensory_pipeline_full_execution():
    """五感拡充を含めた EnrichmentAgent の実行パイプライン結合テスト"""
    chapter_text = (
        "雨が静かに降り注いでいた。\n\n"
        "シンは瓦礫の上に立ち尽くしていた。\n"
        "仲間を失った彼は悲しかった。\n"
        "「なぜこんなことになったんだ」\n"
        "理不尽な運命に対する怒りが込み上げた。\n"
        "遠くで鳴り響く爆発音に、新兵たちは恐怖を感じていた。\n"
    )

    class MockAsyncLLM:
        async def ainvoke(self, prompt: str):
            if "悲し" in prompt:
                return "頬を冷たい雨が濡らし、世界の色が失われたように視界が滲んだ。"
            elif "怒り" in prompt:
                return "熱い血が全身を駆け巡り、掌に爪が食い込むほど拳を固く握りしめた。"
            elif "恐怖" in prompt:
                return "背筋を冷たい悪寒が駆け抜け、浅い呼吸とともに心臓が早鐘を打った。"
            return "五感の詳細描写。"

    agent = EnrichmentAgent(llm=MockAsyncLLM())
    agent._config["enabled"] = True
    agent._config["sensory_expansion"]["enabled"] = True
    agent._config["trivia_insertion"]["enabled"] = False
    agent._config["citation_attachment"]["enabled"] = False
    agent._config["multimedia_scenarios"]["enabled"] = False

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={
            "drafted_text": chapter_text,
            "writing_context": {
                "pov": "三人称",
                "scene_context": "雨の降る戦場、破壊された街",
            },
        },
    )

    result = await agent.execute(ctx)
    assert result.next_agent == AgentName.AUDIT
    assert "enriched_text" in result.artifacts

    enriched_text = result.artifacts["enriched_text"]
    metadata = result.artifacts.get("enrichment_metadata", {})

    # 元のテキストより感覚描写が拡充されて長くなっていること
    assert len(enriched_text) > len(chapter_text)

    # LLMの五感展開が含まれていること
    assert "視界が滲んだ" in enriched_text or "拳を固く握りしめた" in enriched_text

    # [visual] などのデバッグタグが本文に残留していないこと
    import re
    assert not re.search(r'\[[a-zA-Z0-9_]+\]', enriched_text)

    # 五感拡充のメタデータが記録されていること
    sensory_meta = metadata.get("sensory", metadata.get("sensory_expansions", []))
    assert len(sensory_meta) >= 2
    for item in sensory_meta:
        assert "original_phrase" in item
        assert "expanded_text" in item
        assert "emotion" in item
