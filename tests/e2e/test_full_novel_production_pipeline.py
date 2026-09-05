"""End-to-End Test: Full Novel Production Pipeline (Step 69).

Validates the full chain:
1. Blind Gacha Planning (GachaService + BlindReviewGate)
2. Context Construction (FourLayerCompressor + Reflective RAG)
3. Writing (WritingAgent)
4. Enrichment (EnrichmentAgent: Sensory expansion & Trivia budget)
5. 8 Specialist Auditors Evaluation (AuditAggregatorNode -> BookScore)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.entities.easy_mode import GachaRequest
from src.services.blind_review import BlindReviewGate
from src.services.gacha_service import GachaService
from src.services.compression.compressor import FourLayerCompressor
from src.agents.orchestrator import AgentContext, AgentName
from src.agents.writing.agent import WritingAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.specialists.adapter import AuditAggregatorNode


class PipelineMockLLM:
    """Multi-purpose Mock LLM handling gacha, enrichment, and specialist auditing."""

    async def ainvoke(self, prompt: str, **kwargs):
        class Resp:
            def __init__(self, content):
                self.content = content

        text = str(prompt)
        if "Consistency" in text or "矛盾" in text:
            content = '{"score": 90.0, "critique": "設定矛盾はなく、生存状態と行動が論理的です。", "suggestions": []}'
        elif "Creativity" in text or "独創性" in text:
            content = '{"score": 88.0, "critique": "比喩表現が鮮烈で、独創的な世界観が展開されています。", "suggestions": []}'
        elif "Reader Hook" in text or "引きの強さ" in text or "クリフハンガー" in text:
            content = '{"score": 92.0, "critique": "冒頭の謎提示とラストのクリフハンガーが強力です。", "suggestions": []}'
        elif "Emotion Curve" in text or "感情曲線" in text or "カタルシス" in text:
            content = '{"score": 85.0, "critique": "緊張の高まりと結末のカタルシスが秀逸です。", "suggestions": []}'
        elif "Style" in text or "文体" in text or "トーン" in text:
            content = '{"score": 89.0, "critique": "格調高い文体が維持されており、ブレがありません。", "suggestions": []}'
        elif "Factual" in text or "時代考証" in text or "事実関係" in text:
            content = '{"score": 91.0, "critique": "世界観の法則と時代考証が整合しています。", "suggestions": []}'
        elif "Structure" in text or "起承転結" in text or "構成" in text:
            content = '{"score": 87.0, "critique": "プロットの起承転結が綺麗に消化されています。", "suggestions": []}'
        elif "Multimodal" in text or "挿絵" in text:
            content = '{"score": 93.0, "critique": "本文の決戦シーンと挿絵指示の焦点が完璧に一致しています。", "suggestions": []}'
        else:
            content = '{"score": 85.0, "critique": "良好です。", "suggestions": []}'

        return Resp(content)

    def generate(self, prompt: str, **kwargs):
        # Used for enrichment Show Don't Tell
        return "冷たい夜風が首筋を撫で、胸の奥で燻る復讐の炎が静かに燃え上がっていた。"


@pytest.mark.asyncio
async def test_full_novel_production_pipeline_e2e():
    mock_llm = PipelineMockLLM()

    # ---------------------------------------------------------
    # 1. 企画ガチャ (Blind Gacha Planning)
    # ---------------------------------------------------------
    gacha_llm = MagicMock()
    gacha_llm.generate_json = AsyncMock(
        side_effect=[
            {
                "story_content": {
                    "title": "王道：星詠みの剣士",
                    "logline": "星の声を聴く少年が滅びゆく帝国を救うため聖剣を執る。",
                    "protagonist_summary": "純粋な少年剣士セシル",
                    "charm_point": "星魔法と剣戟の爽快な覚醒バトル",
                }
            },
            {
                "story_content": {
                    "title": "変化球：魔道具修理店の日常",
                    "logline": "元勇者が片田舎で訳あり魔道具を修理するほのぼの日常劇。",
                    "protagonist_summary": "隠居した最強勇者",
                    "charm_point": "心温まる人間ドラマ",
                }
            },
            {
                "story_content": {
                    "title": "ダーク：黒曜の復讐者",
                    "logline": "仲間を裏切られた暗殺者が影から全てを裁く。",
                    "protagonist_summary": "冷徹な暗殺者",
                    "charm_point": "知略を尽くしたサスペンス",
                }
            },
        ]
    )

    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_db.get_session = MagicMock()
    mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.get_session.return_value.__aexit__ = AsyncMock()

    mock_event_bus = MagicMock()
    mock_event_bus.publish_blind = AsyncMock()

    gate = BlindReviewGate(
        forbidden_agents=["proposal_other", "plan_other"],
        mode="scrub",
    )

    gacha_service = GachaService(
        llm_service=gacha_llm,
        db=mock_db,
        blind_gate=gate,
        event_bus=mock_event_bus,
    )

    request = GachaRequest(
        genre="fantasy",
        keywords=["剣", "星", "帝国"],
        temperature=0.7,
    )

    gacha_response = await gacha_service.generate_plans(request)
    assert len(gacha_response.plans) == 3
    recommended_plan = next(p for p in gacha_response.plans if p.is_recommended)
    assert recommended_plan is not None

    selected_title = recommended_plan.title
    selected_logline = recommended_plan.logline

    # ---------------------------------------------------------
    # 2. コンテキスト構築 (4階層コンテキスト圧縮)
    # ---------------------------------------------------------
    raw_context = {
        "world_bible": {
            "characters": {
                "セシル": {"alive": True, "status": "active", "weapon": "星詠みの剣"},
                "帝国将軍": {"alive": True, "status": "enemy"},
            },
            "world_rules": {"magic": "星の光を宿した鉱石によるマナ制御"},
        },
        "plot": {
            "title": selected_title,
            "summary": selected_logline,
            "chapter_1": "城門の前での対峙と抜刀",
        },
        "social_dynamics": {"セシル_帝国将軍": {"tension": 95, "trust": 5}},
    }

    from src.services.compression.models import CompressionConfig

    compressor = FourLayerCompressor(config=CompressionConfig(max_tokens=1200))
    raw_text = f"【世界観設定】\n{raw_context['world_bible']}\n【プロット】\n{raw_context['plot']}"
    compressed_result = compressor.compress(raw_text)

    assert compressed_result.final_context_text is not None
    assert compressed_result.final_token_count <= 1200

    # ---------------------------------------------------------
    # 3. 執筆エージェント (WritingAgent)
    # ---------------------------------------------------------
    mock_generator = MagicMock()
    mock_generator.generate_episodes_pipeline = AsyncMock(return_value=(1200, []))

    mock_chapter = MagicMock()
    mock_chapter.content = (
        "城門の前でセシルは息を殺した。なぜ帝国はここまで追ってきたのか？冷たい雨が降り注ぐ中、彼は星詠みの剣を抜刀した。"
    )
    mock_repo = MagicMock()
    mock_repo.get_chapter = AsyncMock(return_value=mock_chapter)
    mock_repo.save_chapter = AsyncMock()

    writing_agent = WritingAgent(repo=mock_repo)
    writing_agent._generator = mock_generator

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={
            "writing_context": {
                "plot": {"summary": "第1話：城門の対峙"},
                "pov": "三人称",
                "scene_context": compressed_result.final_context_text,
            },
            "target_word_count": 1000,
            "plot_tree": "城門への到達 → 追っ手との対峙 → 抜刀",
            "illustration_prompt": "雨の降る城門の前、青い星光を纏う剣を構える少年剣士セシル",
            "illustration_prompts": "雨の降る城門の前、青い星光を纏う剣を構える少年剣士セシル",
            "style_dna": {"tone": "heroic", "person": "third_person"},
            "world_bible": raw_context["world_bible"],
        },
    )

    writing_result = await writing_agent.execute(ctx)
    assert writing_result.next_agent == AgentName.ENRICHMENT
    assert "drafted_text" in writing_result.artifacts

    # ---------------------------------------------------------
    # 4. エンリッチメントエージェント (EnrichmentAgent)
    # ---------------------------------------------------------
    ctx.artifacts.update(writing_result.artifacts)
    enrichment_agent = EnrichmentAgent(llm=mock_llm)
    enrichment_agent._config["enabled"] = True
    enrichment_agent._config["sensory_expansion"] = {"enabled": True}
    enrichment_agent._config["trivia_insertion"] = {"enabled": True, "token_budget": 500}

    enrichment_result = await enrichment_agent.execute(ctx)
    assert enrichment_result.next_agent == AgentName.AUDIT
    assert "enriched_text" in enrichment_result.artifacts

    enriched_text = enrichment_result.artifacts["enriched_text"]
    assert "[visual]" not in enriched_text
    assert len(enriched_text) > 0

    # ---------------------------------------------------------
    # 5. 8専門オーディター集約監査 (AuditAggregatorNode -> BookScore)
    # ---------------------------------------------------------
    from src.services.audit_aggregator import AuditAggregator
    from src.agents.specialists.adapter import load_audit_weights
    from src.agents.specialists import (
        ConsistencyAuditor,
        CreativityAuditor,
        ReaderHookAuditor,
        EmotionCurveAuditor,
        StyleAuditor,
        FactualAuditor,
        StructureAuditor,
        MultimodalAuditor,
    )

    specialists = [
        ConsistencyAuditor(llm=mock_llm),
        CreativityAuditor(llm=mock_llm),
        ReaderHookAuditor(llm=mock_llm),
        EmotionCurveAuditor(llm=mock_llm),
        StyleAuditor(llm=mock_llm),
        FactualAuditor(llm=mock_llm),
        StructureAuditor(llm=mock_llm),
        MultimodalAuditor(llm=mock_llm),
    ]
    weights = load_audit_weights()
    aggregator = AuditAggregator(specialists=specialists, weights=weights)
    audit_node = AuditAggregatorNode(aggregator=aggregator)

    ctx.artifacts.update(enrichment_result.artifacts)
    audit_result = await audit_node.execute(ctx)
    assert audit_result.error is None
    assert "audit_report" in audit_result.artifacts
    assert "audit_score" in audit_result.artifacts
    assert "specialist_scores" in audit_result.artifacts

    overall_score = audit_result.artifacts["audit_score"]
    specialist_scores = audit_result.artifacts["specialist_scores"]

    # 8専門家の全スコアが算出されていること
    assert len(specialist_scores) == 8
    for sp_name, sp_score in specialist_scores.items():
        assert 70.0 <= sp_score <= 100.0, f"Specialist {sp_name} score unexpected: {sp_score}"

    # 総合 BookScore が 80点以上
    assert 80.0 <= overall_score <= 100.0
    # lowest_dimension が特定されていること
    assert audit_result.artifacts.get("lowest_dimension") is not None
