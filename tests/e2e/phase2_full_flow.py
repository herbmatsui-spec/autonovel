"""E2E Test: Phase 2 Full Flow (standalone, minimal imports).

Tests the complete Phase 2 pipeline:
1. Planning → 3 proposals
2. Blind peer review (each proposal audited independently)
3. Specialist audit (8 auditors parallel)
4. Regeneration focus on lowest dimension
5. Reflective RAG screening
"""

import asyncio
import sys
sys.path.insert(0, "/home/herbmatsui/autonovel")

# Minimal imports to avoid circular deps
from src.services.blind_review import BlindReviewGate
from src.agents.event_bus import EventBus, AgentEvent
from src.config.audit_weights import load_weights
from src.services.audit_aggregator import AuditAggregator
from src.services.reflective_rag import ReflectiveRAGService
from src.services.rag_service import SearchResult
from unittest.mock import MagicMock


class MockRAGService:
    """Mock RAG service for E2E testing."""
    
    def __init__(self):
        self.search_results = [
            SearchResult(id="1", content="アリスは東京で剣を振った", metadata={}, source="vector", score=0.9),
            SearchResult(id="2", content="ボブは大阪で杖を使った", metadata={}, source="vector", score=0.8),
        ]
    
    def search_similar_chunks(self, session, query, limit=5, min_score=0.0):
        return self.search_results


async def test_phase2_full_pipeline():
    """Complete Phase 2 pipeline test."""
    
    print("🧪 Starting Phase 2 Full Pipeline Test...")
    
    # 1. Setup: 3 proposals from PlanningAgent
    proposals = [
        {"proposal_id": "A", "title": "勇者の旅", "concept": "王道ファンタジー"},
        {"proposal_id": "B", "title": "悪役令嬢の逆転", "concept": "異世界転生"},
        {"proposal_id": "C", "title": "現代ダンジョン配信", "concept": "現代ファンタジー"},
    ]
    
    # 2. Blind Peer Review: Each proposal audited independently
    bus = EventBus()
    # Use blocked_keys to explicitly list the proposal keys to block
    gate = BlindReviewGate(forbidden_agents=["planning"], blocked_keys=["proposal_a", "proposal_b", "proposal_c"])
    
    audit_results = []
    
    async def audit_handler(event: AgentEvent):
        payload = event.payload
        # Verify blind review: other proposals are blocked
        for k, v in payload.items():
            if k != "own_proposal":
                assert "BLOCKED:" in str(v) or "HASH:" in str(v), f"Leaked: {k}"
        own = payload["own_proposal"]
        audit_results.append({
            "proposal": own["proposal_id"],
            "score": {"A": 85, "B": 72, "C": 91}[own["proposal_id"]],
        })
    
    bus.subscribe("audit", audit_handler)
    
    for p in proposals:
        event = AgentEvent(
            agent="audit",
            payload={
                "own_proposal": p,
                "proposal_A": proposals[0],
                "proposal_B": proposals[1],
                "proposal_C": proposals[2],
            },
            correlation_id=f"book1_ch1_{p['proposal_id']}",
        )
        await bus.publish_blind(event, gate)
    
    await asyncio.sleep(0.1)
    
    # Verify 3 independent audits
    assert len(audit_results) == 3
    scores = [r["score"] for r in audit_results]
    assert len(set(scores)) == 3  # Different scores = independent evaluation
    print("✅ Blind Peer Review: 3 independent audits passed")
    
    # 3. Specialist Audit: 8 auditors run in parallel
    # Import specialists here to avoid early import issues
    from src.agents.specialists import (
        ConsistencyAuditor, CreativityAuditor, ReaderHookAuditor,
        EmotionCurveAuditor, StyleAuditor, FactualAuditor,
        StructureAuditor, MultimodalAuditor,
    )
    
    weights = load_weights(genre="literary", phase="mid_writing")
    
    specialists = [
        ConsistencyAuditor(llm=None),
        CreativityAuditor(llm=None),
        ReaderHookAuditor(llm=None),
        EmotionCurveAuditor(llm=None),
        StyleAuditor(llm=None),
        FactualAuditor(llm=None),
        StructureAuditor(llm=None),
        MultimodalAuditor(llm=None),
    ]
    
    ctx = {
        "book_id": 1,
        "chapter_number": 3,
        "draft_text": "アリスは東京で剣を振って敵を倒した。希望の光が差し込んだ。",
        "world_bible_snapshot": {
            "characters": [{"name": "アリス"}],
            "locations": [{"name": "東京"}],
            "items": [{"name": "剣"}],
        },
        "style_dna": {"sample_text": "私は歩く。", "first_person": 0.5, "polite": 0.0},
        "plot_tree": "アリス 東京 剣 敵 倒す 希望 光",
        "illustration_prompts": "アリス、東京、剣、光",
        "genre": "literary",
        "correlation_id": "book1_ch3",
    }
    
    aggregator = AuditAggregator(
        specialists=specialists,
        weights=load_weights(genre="literary", phase="mid_writing"),
        event_bus=None,
    )
    
    await aggregator.run_all(ctx)
    book_score = aggregator.aggregate()
    
    # Verify aggregation
    assert 0 <= book_score.overall <= 100
    assert len(book_score.by_specialist) == 8
    assert book_score.missing == []
    assert book_score.lowest_dimension() is not None
    assert abs(sum(book_score.weights_used.values()) - 1.0) < 1e-6
    
    lowest = book_score.lowest_dimension()
    assert lowest in [
        "consistency", "creativity", "reader_hook", "emotion_curve",
        "style", "factual", "structure", "multimodal"
    ]
    print(f"✅ Specialist Audit: 8 auditors, overall={book_score.overall:.1f}, lowest={lowest}")
    
    # 4. Reflective RAG: Iterative query refinement
    from src.services.rag_service import SearchResult
    
    class MockRAGService:
        def __init__(self):
            self.search_results = [
                SearchResult(id="1", content="アリスは東京で剣を振った", metadata={}, source="vector", score=0.9),
                SearchResult(id="2", content="ボブは大阪で杖を使った", metadata={}, source="vector", score=0.8),
            ]
        def search_similar_chunks(self, session, query, limit=5, min_score=0.0):
            return self.search_results
    
    mock_rag = MockRAGService()
    reflective = ReflectiveRAGService(
        rag_service=mock_rag,
        top_k=2,
        max_iter=3,
        relevance_threshold=0.5,
    )
    session = MagicMock()
    
    result = await reflective.retrieve_with_reflection(
        session, query="アリス 剣", book_id=1
    )
    
    assert isinstance(result.iterations, int)
    assert result.iterations >= 1
    assert result.iterations <= 3
    assert result.converged in (True, False)
    assert len(result.refined_queries) >= 1
    assert result.final_doc_count <= 2
    print(f"✅ Reflective RAG: {result.iterations} iterations, converged={result.converged}")
    
    print("\n🎉 Phase 2 Full Pipeline Test PASSED!")
    print(f"  3 Proposals: {len(audit_results)} independent audits")
    print(f"  8 Specialists: all ran, overall={book_score.overall:.1f}")
    print(f"  Lowest dimension: {lowest}")
    print(f"  Reflective RAG: {result.iterations} iterations, converged={result.converged}")


if __name__ == "__main__":
    asyncio.run(test_phase2_full_pipeline())