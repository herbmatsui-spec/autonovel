"""End-to-End integration tests for Blind Peer Review & Proposal Isolation (Pillar 3 Part 1 & Step 66)."""

import pytest
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


@pytest.mark.asyncio
async def test_blind_review_e2e_isolation_and_purification():
    """E2E Test: 3-Proposal Generation, Sandbox Isolation, Blind Routing, and Leak Purification."""
    
    # 1. Simulate 3 distinct proposal outputs from planning generation
    proposals = [
        {
            "proposal_id": "prop_alpha_001",
            "title": "魔導帝国の反逆者アレン",
            "theme": "復讐と解放のダークファンタジー",
            "characters": ["アレン", "古代竜ファヴニール", "皇帝ベルゼ"],
        },
        {
            "proposal_id": "prop_beta_002",
            "title": "聖女ルチアの美味しい宮廷料理",
            "theme": "料理で世界を救うグルメファンタジー",
            "characters": ["ルチア", "騎士団長レオン", "小竜ポチ"],
        },
        {
            "proposal_id": "prop_gamma_003",
            "title": "電脳都市のサイバー陰陽師",
            "theme": "AI式神とサイバーパンクバトル",
            "characters": ["カイト", "AI式神ツクヨミ", "黒幕マトリクス"],
        },
    ]

    # 2. Execute isolated evaluations in parallel sandboxes
    custom_contexts = {
        p["proposal_id"]: ProposalSandboxContext(
            proposal_id=p["proposal_id"],
            metadata={"proposal": p},
        )
        for p in proposals
    }
    runner = ProposalIsolationRunner(proposal_ids=list(custom_contexts.keys()))
    
    async def mock_eval_fn(sandbox: ProposalSandboxContext):
        p = sandbox.metadata["proposal"]
        if p["proposal_id"] == "prop_alpha_001":
            # Intentional leak of sibling proposal information in raw review
            raw_feedback = (
                f"企画【{p['title']}】は世界観が重厚で魅力的である。"
                f"しかし、A案では重厚すぎるため、聖女ルチアの美味しい宮廷料理のような温かみのあるグルメ要素や、"
                f"ヒロインのルチアのような親しみやすいキャラ配置を検討しても良いのではないか。"
            )
            score = 78
        elif p["proposal_id"] == "prop_beta_002":
            raw_feedback = f"企画【{p['title']}】は読者ターゲットが明確でテンポ良く読める。"
            score = 88
        else:
            raw_feedback = f"企画【{p['title']}】は独自の世界観と斬新なSF設定が際立っている。"
            score = 85

        return {
            "proposal_id": p["proposal_id"],
            "score": score,
            "raw_review": raw_feedback,
        }

    isolation_results = await runner.execute_isolated_proposals(
        generate_fn=mock_eval_fn,
        custom_contexts=custom_contexts,
    )

    assert len(isolation_results) == 3

    # 3. Detect and Purify cross-proposal leaks with BlindFeedbackPurifier
    purifier = BlindFeedbackPurifier()

    purified_reviews = {}
    for res in isolation_results.values():
        pid = res["proposal_id"]
        raw_text = res["raw_review"]
        
        target_prop = next(p for p in proposals if p["proposal_id"] == pid)
        sibling_props = [p for p in proposals if p["proposal_id"] != pid]

        # Gather forbidden terms from sibling proposals
        forbidden_terms = []
        for sib in sibling_props:
            forbidden_terms.append(sib["title"])
            forbidden_terms.extend(sib.get("characters", []))

        # Detect leaks
        leaks = detect_proposal_leaks(raw_text)
        if pid == "prop_alpha_001":
            assert len(leaks) > 0, "Leaks should be detected in prop_alpha_001 review"

        # Purify critique
        purified = purifier.purify_critique(
            raw_text,
            forbidden_terms=forbidden_terms,
        )
        purified_reviews[pid] = purified

    # 4. Assertions on Purification
    alpha_purified = purified_reviews["prop_alpha_001"]
    assert alpha_purified.is_purified is True
    # Verify leak snippets were removed / sanitized
    assert "聖女ルチアの美味しい宮廷料理" not in alpha_purified.purified_text
    assert "ルチア" not in alpha_purified.purified_text
    assert "アレン" in alpha_purified.purified_text  # Own characters preserved

    # 5. Route payload through BlindReviewGate for structured isolation
    gate = BlindReviewGate(forbidden_agents=["proposal_beta", "proposal_gamma"])
    routed_payload = gate.scrub_payload({
        "target": "proposal_alpha",
        "proposal_alpha": {"evaluation": alpha_purified.purified_text},
        "proposal_beta": {"secret_note": "internal metric"},
    })
    assert "proposal_beta" not in routed_payload or "<BLOCKED" in str(routed_payload["proposal_beta"])

    # 6. Verify full dataset integrity via verify_no_cross_proposal_contamination
    clean_proposals_for_verification = [
        {
            "title": proposals[0]["title"],
            "review": alpha_purified.purified_text,
        },
        {
            "title": proposals[1]["title"],
            "review": purified_reviews["prop_beta_002"].purified_text,
        },
        {
            "title": proposals[2]["title"],
            "review": purified_reviews["prop_gamma_003"].purified_text,
        },
    ]
    v_res = verify_no_cross_proposal_contamination(clean_proposals_for_verification)
    assert v_res.passed is True, f"Cross-contamination detected: {v_res.violations}"
