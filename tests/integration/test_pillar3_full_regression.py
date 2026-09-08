"""Comprehensive regression test covering all subsystems of Pillar 3 (Step 70)."""

import pytest
from unittest.mock import MagicMock

# Part 1 imports
from src.services.proposal_isolation import (
    ProposalSandboxContext,
    ProposalIsolationRunner,
)
from src.services.blind_review import (
    BlindFeedbackPurifier,
    BlindReviewGate,
    detect_proposal_leaks,
    verify_no_cross_proposal_contamination,
)

# Part 2 & 3 imports
from src.services.nlp.japanese_tokenizer import JapaneseTokenizer
from src.services.rrf_fusion import compute_rrf_scores
from src.services.query_reformulator import QueryReformulator
from src.services.reflective_rag import ReflectiveRAGService
from src.services.rag_service import SearchResult

# Part 4 & 5 imports
from src.services.compression.layer3_taxonomy import DynamicTaxonomyEngine
from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig, ProtectedContext

# Part 6 imports
from src.agents.context_builder_agent import ContextBuilderAgent


@pytest.mark.asyncio
async def test_pillar3_full_regression():
    """Full end-to-end regression verifying all 6 parts of Pillar 3 in sequence."""
    
    # -------------------------------------------------------------
    # 1. Part 1: Blind Review & Proposal Isolation
    # -------------------------------------------------------------
    proposals = [
        {"proposal_id": "p1", "title": "覇王の帰還", "theme": "成り上がりファンタジー", "characters": ["レイ"]},
        {"proposal_id": "p2", "title": "魔法薬師の日常", "theme": "スローライフ", "characters": ["エマ"]},
    ]
    custom_contexts = {
        p["proposal_id"]: ProposalSandboxContext(proposal_id=p["proposal_id"], metadata={"data": p})
        for p in proposals
    }
    runner = ProposalIsolationRunner(proposal_ids=list(custom_contexts.keys()))

    async def mock_reviewer(sb: ProposalSandboxContext):
        p = sb.metadata["data"]
        # Intentionally inject leak in p1's review mentioning p2
        if p["proposal_id"] == "p1":
            review = f"企画【{p['title']}】は良い。しかし魔法薬師の日常やエマのような癒やしも欲しい。"
        else:
            review = f"企画【{p['title']}】は温かみがある。"
        return {"proposal_id": p["proposal_id"], "review": review}

    raw_evals = await runner.execute_isolated_proposals(mock_reviewer, custom_contexts=custom_contexts)
    assert len(raw_evals) == 2

    # Purify critique
    purifier = BlindFeedbackPurifier()
    p1_purified = purifier.purify_critique(raw_evals["p1"]["review"], forbidden_terms=["魔法薬師の日常", "エマ"])
    assert p1_purified.is_purified is True
    assert "魔法薬師の日常" not in p1_purified.purified_text
    assert "エマ" not in p1_purified.purified_text

    # Gate verification
    gate = BlindReviewGate(forbidden_agents=["p2"])
    scrubbed = gate.scrub_payload({"p2": "private_note", "p1": p1_purified.purified_text})
    assert "<BLOCKED:p2>" in scrubbed["p2"]

    # -------------------------------------------------------------
    # 2. Part 2: Japanese NLP & Hybrid RRF
    # -------------------------------------------------------------
    tokenizer = JapaneseTokenizer()
    tokens = tokenizer.tokenize("レイは聖なる魔導槍を手にして魔王城へ進軍した。")
    assert len(tokens) >= 5

    dense_candidates = [{"id": "docA", "content": "魔導槍の設定"}, {"id": "docB", "content": "魔王城の地形"}]
    sparse_candidates = [{"id": "docB", "content": "魔王城の地形"}, {"id": "docC", "content": "王都の守備軍"}]
    rrf_res = compute_rrf_scores(dense_candidates, sparse_candidates, k=60)
    assert len(rrf_res) == 3
    # docB was in both, should have highest score
    assert rrf_res[0].doc_id == "docB"

    # -------------------------------------------------------------
    # 3. Part 3: Semantic Reflective RAG & Consistency
    # -------------------------------------------------------------
    qr = QueryReformulator()
    expanded_q = qr.reformulate_query("魔王城 攻略", keywords=["魔導槍", "聖属性"], scene_intent="突入作戦")
    assert "魔王城" in expanded_q

    mock_rag = MagicMock()
    mock_rag.age_client = None
    mock_rag.search_similar_chunks.return_value = [
        SearchResult(id="1", content="魔導槍は古代の英霊が遺した神器。", metadata={"name": "魔導槍", "status": "active"}, source="item", score=0.9),
        SearchResult(id="2", content="先代魔王は百年前に封印された。", metadata={"name": "先代魔王", "status": "sealed"}, source="lore", score=0.85),
    ]
    rag_service = ReflectiveRAGService(rag_service=mock_rag, relevance_threshold=0.5)
    rag_output = await rag_service.retrieve_with_reflection(
        session=MagicMock(),
        query=expanded_q,
        scene_intent="突入作戦",
        top_k=2,
    )
    # The sealed entity should be filtered or flagged
    formatted_rag = rag_service.format_for_prompt(rag_output)
    assert "魔導槍" in formatted_rag

    # -------------------------------------------------------------
    # 4. Part 4 & 5: Dynamic Taxonomy & 4-Layer Context Compression
    # -------------------------------------------------------------
    tax = DynamicTaxonomyEngine()
    inferred_cat = tax.generalize("暗黒騎士団長", context="敵勢力の司令官")
    assert len(inferred_cat) > 0

    entities = [
        {"name": "レイ", "labels": ["Hero"], "properties": {"role": "主人公"}},
        {"name": "魔導槍", "labels": ["Item"], "properties": {"role": "神器"}},
        {"name": "魔王城", "labels": ["Location"], "properties": {"role": "敵本拠地"}},
        {"name": "FS-REI-DESTINY", "labels": ["Foreshadowing"], "properties": {"role": "宿命の伏線"}},
    ]
    relations = [
        {"source": "レイ", "target": "魔導槍", "type": "装備"},
        {"source": "レイ", "target": "魔王城", "type": "侵攻"},
    ]
    raw_story = ("第10話：決戦。\nレイは魔導槍を握りしめ、魔王城の階段を駆け上がった。未回収伏線 FS-REI-DESTINY が鳴動する。\n") * 10

    protected = ProtectedContext(
        active_characters=["レイ"],
        pending_foreshadowing_ids=["FS-REI-DESTINY"],
        pinned_entities={"魔導槍"},
    )
    compressor = FourLayerCompressor(config=CompressionConfig(max_tokens=400, cache_enabled=False))
    comp_res = compressor.compress(
        raw_text=raw_story,
        entities=entities,
        relations=relations,
        scene_type="combat",
        max_tokens=400,
        protected_context=protected,
        bypass_cache=True,
    )
    assert comp_res.final_token_count <= 400
    retained = set(comp_res.layer4.retained_entities)
    assert "レイ" in retained
    assert "魔導槍" in retained
    assert "FS-REI-DESTINY" in retained

    # -------------------------------------------------------------
    # 5. Part 6: Context Builder Agent Integration
    # -------------------------------------------------------------
    cba = ContextBuilderAgent()
    budgets = cba.allocate_token_budgets(total_budget=3000, scene_type="combat")
    assert budgets["rag_budget"] + budgets["compression_budget"] == 3000

    # Final verification of combined context
    final_combined = (
        f"{formatted_rag}\n\n"
        f"{comp_res.layer4.compressed_text}\n"
    )
    assert "レイ" in final_combined
    assert "魔導槍" in final_combined

    print("=== Pillar 3 Comprehensive Full Regression Passed! ===")
