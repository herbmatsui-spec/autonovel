"""End-to-End integration test for Reflective RAG, 4-Layer Compression, and Context Feeding (Step 67)."""

import pytest
from unittest.mock import MagicMock

from src.services.query_reformulator import QueryReformulator
from src.services.reflective_rag import ReflectiveRAGService
from src.services.rag_service import SearchResult
from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig, ProtectedContext
from src.agents.context_builder_agent import ContextBuilderAgent


@pytest.mark.asyncio
async def test_semantic_rag_compression_e2e():
    """E2E Test: HyDE query expansion -> Reflective RAG retrieval -> 4-layer protected compression -> Context builder prompt."""
    
    # 1. Setup Query Reformulator & Reflective RAG Service
    mock_rag = MagicMock()
    mock_rag.age_client = None
    mock_session = MagicMock()

    mock_rag.search_similar_chunks.return_value = [
        SearchResult(
            id="1",
            content="フェルディナントは第3皇子であり、真祖の吸血鬼に滅ぼされた古都ルミエルの唯一の生き残り。",
            metadata={"name": "フェルディナント", "status": "active"},
            source="character_lore",
            score=0.92,
        ),
        SearchResult(
            id="2",
            content="聖剣アスカロンは龍殺しの加護を宿し、真祖の眷属に対して絶対的な特効を持つ。",
            metadata={"name": "聖剣アスカロン", "status": "active"},
            source="equipment",
            score=0.88,
        ),
        SearchResult(
            id="3",
            content="帝都防衛戦において第2騎士団が全滅し、西の城壁が崩壊寸前となっている。",
            metadata={"name": "西の城壁", "status": "active"},
            source="world_event",
            score=0.81,
        ),
    ]

    rag_service = ReflectiveRAGService(rag_service=mock_rag, relevance_threshold=0.5)
    
    # 2. Reflective query rewrite and retrieval
    scene_intent = "フェルディナントが聖剣を抜いて真祖の吸血鬼と対峙する決戦シーン"
    rag_result = await rag_service.retrieve_with_reflection(
        session=mock_session,
        query="フェルディナント 聖剣 アスカロン 吸血鬼",
        scene_intent=scene_intent,
        top_k=3,
    )

    assert rag_result.converged is True
    assert len(rag_result.documents) > 0
    formatted_prompt = rag_service.format_for_prompt(rag_result)
    assert "【参照世界観設定（反射的整合性検証済）】" in formatted_prompt
    assert "フェルディナント" in formatted_prompt
    assert "聖剣アスカロン" in formatted_prompt

    # 3. Setup Knowledge Base Graph & Raw Text for FourLayerCompressor
    entities = [
        {"name": "フェルディナント", "labels": ["Person", "Hero"], "properties": {"role": "第3皇子"}},
        {"name": "真祖の吸血鬼ヴァラキア", "labels": ["Person", "Enemy"], "properties": {"role": "ボス"}},
        {"name": "聖剣アスカロン", "labels": ["Item", "Relic"], "properties": {"role": "龍殺しの神剣"}},
        {"name": "古都ルミエル", "labels": ["Location"], "properties": {"role": "滅亡した都市"}},
        {"name": "西の城壁", "labels": ["Location"], "properties": {"role": "戦場"}},
        {"name": "第2騎士団", "labels": ["Group"], "properties": {"role": "壊滅部隊"}},
        {"name": "帝都", "labels": ["Location"], "properties": {"role": "首都"}},
        {"name": "FS-HOLY-SWORD", "labels": ["Foreshadowing"], "properties": {"role": "未回収伏線"}},
    ]
    relations = [
        {"source": "フェルディナント", "target": "聖剣アスカロン", "type": "装備および契約"},
        {"source": "フェルディナント", "target": "真祖の吸血鬼ヴァラキア", "type": "宿命の宿敵"},
        {"source": "真祖の吸血鬼ヴァラキア", "target": "古都ルミエル", "type": "破壊および虐殺"},
        {"source": "フェルディナント", "target": "西の城壁", "type": "防衛参戦"},
        {"source": "第2騎士団", "target": "西の城壁", "type": "殉職防衛"},
    ]

    raw_episode_summary = (
        "第48話：破滅の足音。\n"
        + "夕闇迫る帝都の空を紅蓮の血霧が覆い、真祖の吸血鬼ヴァラキアの降臨を告げていた。\n"
        + "かつて古都ルミエルを一夜で焦土と化した悪夢の怪異が、今まさに西の城壁へと迫る。\n"
        + "第2騎士団の奮戦むなしく城門は破られ、守備兵たちの絶叫が響き渡る。\n"
        + "そのとき、白銀の甲冑を纏った第3皇子フェルディナントが、青く輝く聖剣アスカロンを抜き放ち、単身城壁へと登った。\n"
        + "彼の瞳には故郷の仇を討つという冷徹な決意と、未回収の伏線 FS-HOLY-SWORD の真名解放の予兆が宿っていた。\n"
    ) * 8  # Expand length to test compression

    # 4. Protected Context configuration
    protected = ProtectedContext(
        active_characters=["フェルディナント", "真祖の吸血鬼ヴァラキア"],
        pending_foreshadowing_ids=["FS-HOLY-SWORD"],
        pinned_entities={"聖剣アスカロン"},
    )

    compressor = FourLayerCompressor(
        config=CompressionConfig(max_tokens=600, target_reduction_ratio=0.5, cache_enabled=False)
    )

    compression_result = compressor.compress(
        raw_text=raw_episode_summary,
        entities=entities,
        relations=relations,
        scene_type="combat",
        max_tokens=600,
        protected_context=protected,
        bypass_cache=True,
    )

    assert compression_result.final_token_count <= 600
    assert compression_result.overall_reduction_ratio >= 0.45
    retained_set = set(compression_result.layer4.retained_entities)
    assert "フェルディナント" in retained_set
    assert "真祖の吸血鬼ヴァラキア" in retained_set
    assert "聖剣アスカロン" in retained_set
    assert "FS-HOLY-SWORD" in retained_set

    # 5. Verify ContextBuilderAgent Token Budgeting & Pipeline Assembly
    agent = ContextBuilderAgent()
    budgets = agent.allocate_token_budgets(
        total_budget=4000,
        scene_type="combat",
    )
    assert "rag_budget" in budgets
    assert "compression_budget" in budgets
    assert budgets["rag_budget"] + budgets["compression_budget"] == 4000
    # In combat scene, compressed story/knowledge context is prioritized over RAG lore
    assert budgets["compression_budget"] > budgets["rag_budget"]

    # 6. Format final injection context
    compressed_text = compression_result.layer4.compressed_text

    final_prompt_context = (
        f"# 執筆背景設定 (Semantic RAG)\n{formatted_prompt}\n\n"
        f"# 圧縮世界観・現在状況 (FourLayer Compressed)\n{compressed_text}\n"
    )

    assert "【参照世界観設定（反射的整合性検証済）】" in final_prompt_context
    assert "【現在同席】" in final_prompt_context
    assert "フェルディナント" in final_prompt_context
    assert "真祖の吸血鬼ヴァラキア" in final_prompt_context

    print("E2E Semantic RAG & Compression Test Passed.")
