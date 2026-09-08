"""Diagnostic Health Check for Pillar 3: Semantic RAG & Context Compression (Step 68)."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import time
from typing import Dict, Any

def run_health_checks() -> int:
    print("==========================================================")
    print("   Pillar 3: Semantic RAG & Compression Health Check      ")
    print("==========================================================")
    
    results: Dict[str, bool] = {}
    
    # 1. Japanese Tokenizer Check
    try:
        from src.services.nlp.japanese_tokenizer import JapaneseTokenizer
        tok = JapaneseTokenizer()
        tokens = tok.tokenize("勇者カイトは伝説の聖剣を抜いて魔王を倒した。")
        assert len(tokens) > 0
        results["JapaneseTokenizer"] = True
        print("[PASS] 1. JapaneseTokenizer (Sudachi / Regex fallback)")
    except Exception as e:
        results["JapaneseTokenizer"] = False
        print(f"[FAIL] 1. JapaneseTokenizer: {e}")

    # 2. RRF Fusion Check
    try:
        from src.services.rrf_fusion import compute_rrf_scores
        dense = [{"id": "doc1", "content": "c1"}, {"id": "doc2", "content": "c2"}]
        sparse = [{"id": "doc2", "content": "c2"}, {"id": "doc3", "content": "c3"}]
        fused = compute_rrf_scores(dense, sparse, k=60)
        assert len(fused) == 3
        results["RRFFusion"] = True
        print("[PASS] 2. RRF Fusion (Reciprocal Rank Fusion)")
    except Exception as e:
        results["RRFFusion"] = False
        print(f"[FAIL] 2. RRF Fusion: {e}")

    # 3. Query Reformulator Check
    try:
        from src.services.query_reformulator import QueryReformulator
        qr = QueryReformulator()
        rewritten = qr.reformulate_query(
            query="魔法少女",
            keywords=["魔力", "契約"],
            scene_intent="暗黒街での戦闘",
            mode="intent_guided",
        )
        assert len(rewritten) > 0
        results["QueryReformulator"] = True
        print("[PASS] 3. QueryReformulator (Intent Guided Reformulation)")
    except Exception as e:
        results["QueryReformulator"] = False
        print(f"[FAIL] 3. QueryReformulator: {e}")

    # 4. Reflective RAG Service Fit Check
    try:
        from unittest.mock import MagicMock
        from src.services.reflective_rag import ReflectiveRAGService
        from src.services.rag_service import SearchResult
        mock_rag = MagicMock()
        mock_rag.age_client = None
        service = ReflectiveRAGService(rag_service=mock_rag)
        doc = SearchResult(id="1", content="大賢者は生きていた", metadata={"status": "dead"}, source="world", score=0.9)
        fit = service._context_fit_check(MagicMock(), doc)
        assert fit.is_retired is True
        results["ReflectiveRAGFit"] = True
        print("[PASS] 4. Reflective RAG World Bible Consistency Filter")
    except Exception as e:
        results["ReflectiveRAGFit"] = False
        print(f"[FAIL] 4. Reflective RAG World Bible Consistency Filter: {e}")

    # 5. Dynamic Taxonomy Engine Check
    try:
        from src.services.compression.layer3_taxonomy import DynamicTaxonomyEngine
        tax = DynamicTaxonomyEngine()
        cat = tax.generalize("エルヴィン騎士団長", context="王国の軍事組織")
        assert cat is not None and len(cat) > 0
        results["DynamicTaxonomy"] = True
        print(f"[PASS] 5. Dynamic Taxonomy Engine (Generalization: {cat})")
    except Exception as e:
        results["DynamicTaxonomy"] = False
        print(f"[FAIL] 5. Dynamic Taxonomy Engine: {e}")

    # 6. Four-Layer Context Compression Check
    try:
        from src.services.compression.compressor import FourLayerCompressor
        from src.services.compression.models import CompressionConfig, ProtectedContext
        comp = FourLayerCompressor(config=CompressionConfig(max_tokens=200, cache_enabled=False))
        prot = ProtectedContext(active_characters=["アレン"], pending_foreshadowing_ids=["FS-1"])
        c_res = comp.compress(
            raw_text="アレンは剣を抜いた。" * 20,
            entities=[{"name": "アレン", "labels": ["Hero"], "properties": {}}, {"name": "FS-1", "labels": ["Foreshadowing"], "properties": {}}],
            relations=[],
            scene_type="combat",
            max_tokens=200,
            protected_context=prot,
            bypass_cache=True,
        )
        assert "アレン" in c_res.layer4.retained_entities
        results["FourLayerCompression"] = True
        print("[PASS] 6. Four-Layer Context Compression & Protected Retention")
    except Exception as e:
        results["FourLayerCompression"] = False
        print(f"[FAIL] 6. Four-Layer Context Compression: {e}")

    # 7. Blind Review Gate & Proposal Sandbox Check
    try:
        from src.services.blind_review import BlindReviewGate, BlindFeedbackPurifier, detect_proposal_leaks
        from src.services.proposal_isolation import ProposalSandboxContext
        gate = BlindReviewGate(forbidden_agents=["proposal_b"])
        scrubbed = gate.scrub_payload({"proposal_b": "secret", "clean": "public"})
        assert "<BLOCKED:proposal_b>" in scrubbed["proposal_b"]
        purifier = BlindFeedbackPurifier()
        purified = purifier.purify_critique("B案の展開は早い", forbidden_terms=["B案"])
        assert purified.is_purified is True
        results["BlindReviewGate"] = True
        print("[PASS] 7. Blind Review Gate & Proposal Sandbox Isolation")
    except Exception as e:
        results["BlindReviewGate"] = False
        print(f"[FAIL] 7. Blind Review Gate & Proposal Sandbox Isolation: {e}")

    print("----------------------------------------------------------")
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"Summary: {passed_count}/{total_count} components passed health check.")
    print("==========================================================")
    
    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(run_health_checks())
