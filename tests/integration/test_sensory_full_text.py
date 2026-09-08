"""Integration tests for sensory expansion on full-length novel chapter text (Part 3, Step 35)."""
import pytest
from src.agents.orchestrator import AgentContext, AgentName
from src.agents.enrichment_agent import EnrichmentAgent


@pytest.mark.asyncio
async def test_sensory_full_chapter_text_grammar_integrity():
    """長文小説テキストに対する五感拡充処理の文法整合性と会話文保護の結合テスト"""
    paragraphs = [
        "冷たい雨が夜の街を濡らしていた。石畳の路地に黒い影が伸びる。",
        "シンは崩れたレンガの壁に背を預けていた。仲間を失った彼は悲しかったが、足を止めるわけにはいかなかった。",
        "「おい、シン！ まだ息はあるか！」",
        "仲間の声が遠くから聞こえた。",
        "「ああ、なんとか生きてるよ。でも、あいつらのやり方は許せない」",
        "胸の奥底から湧き上がる激怒を感じていたが、シンは深呼吸をして冷静さを取り戻そうとした。",
        "廃墟の奥から不気味な咆哮が響いた。若い兵士たちは恐怖に震えていたものの、武器を構えて前進した。",
        "戦いの果てに、ようやく光が差し込んだ。生き残った彼らは嬉しかった。",
        "「終わったんだな」と呟きながら、シンは天を仰いだ。",
    ]
    full_text = "\n\n".join(paragraphs)

    class MockLongTextLLM:
        async def ainvoke(self, prompt: str):
            if "悲し" in prompt:
                return "頬を伝う雨水が冷たく肌を刺し、滲む視界の先をただ睨み据えた。"
            elif "激怒" in prompt or "怒り" in prompt:
                return "熱い血潮が首筋を駆け上り、掌に爪が食い込むほど拳を握りしめた。"
            elif "恐怖" in prompt:
                return "背筋を凍りつくような悪寒が走り、浅い呼吸とともに心臓が早鐘を打った。"
            elif "嬉し" in prompt:
                return "冷え切った身体に温かな陽射しが染み渡り、強ばっていた肩の力がふっと抜けた。"
            return "五感の情景描写が広がる。"

    agent = EnrichmentAgent(llm=MockLongTextLLM())
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
            "drafted_text": full_text,
            "writing_context": {
                "pov": "三人称",
                "scene_context": "雨の降りしきる廃墟都市の激戦直後",
            },
        },
    )

    result = await agent.execute(ctx)
    assert result.next_agent == AgentName.AUDIT
    assert "enriched_text" in result.artifacts
    enriched_text = result.artifacts["enriched_text"]
    metadata = result.artifacts.get("enrichment_metadata", {})
    sensory_meta = metadata.get("sensory", [])

    # 1. 会話文が一切破壊されていないこと（「おい、シン！ まだ息はあるか！」などそのまま残存）
    assert "「おい、シン！ まだ息はあるか！」" in enriched_text
    assert "「ああ、なんとか生きてるよ。でも、あいつらのやり方は許せない」" in enriched_text
    assert "「終わったんだな」と呟きながら、シンは天を仰いだ。" in enriched_text

    # 2. 地の文の感情表現が五感描写に拡充されていること
    assert len(enriched_text) > len(full_text)
    assert "頬を伝う雨水が冷たく肌を刺し" in enriched_text or "熱い血潮が首筋を駆け上り" in enriched_text

    # 3. 句読点エラー（。。や。が）やタグが残存していないこと
    import re
    assert "。。" not in enriched_text
    assert "。が" not in enriched_text
    assert "。けれど" not in enriched_text
    assert not re.search(r'\[[a-zA-Z0-9_]+\]', enriched_text)

    # 4. メタデータに複数箇所の文単位リライト差分が記録されていること
    assert len(sensory_meta) >= 3
    for item in sensory_meta:
        assert "original_sentence" in item
        assert "expanded_text" in item
        assert "emotion" in item
