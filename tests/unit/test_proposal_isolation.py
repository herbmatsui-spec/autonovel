"""Unit tests for proposal isolation and cross-proposal leak detection (Part 1 / Steps 7-12)."""

import pytest
from unittest.mock import AsyncMock

from src.services.blind_review import (
    BlindReviewGate,
    IsolationSchema,
    verify_no_cross_proposal_contamination,
)
from src.services.proposal_isolation import (
    ProposalSandboxContext,
    ProposalIsolationRunner,
)


def test_proposal_sandbox_context_isolation():
    """Test that multiple sandbox contexts maintain independent state (Step 7)."""
    ctx1 = ProposalSandboxContext.create(proposal_id="prop_a")
    ctx2 = ProposalSandboxContext.create(proposal_id="prop_b")

    assert ctx1.proposal_id == "prop_a"
    assert ctx2.proposal_id == "prop_b"
    assert ctx1.session_id != ctx2.session_id

    ctx1.add_history("system", "System prompt A")
    ctx1.store_artifact("plot", "Plot details A")

    assert len(ctx1.isolated_history) == 1
    assert len(ctx2.isolated_history) == 0
    assert "plot" in ctx1.artifacts
    assert "plot" not in ctx2.artifacts


@pytest.mark.asyncio
async def test_proposal_isolation_runner():
    """Test that runner executes proposal generators in physically isolated sandboxes (Step 8)."""
    runner = ProposalIsolationRunner()

    async def mock_generator(sandbox: ProposalSandboxContext):
        sandbox.add_history("assistant", f"Generated concept for {sandbox.proposal_id}")
        return {
            "title": f"Story {sandbox.proposal_id}",
            "concept": f"Independent world {sandbox.session_id}",
        }

    results = await runner.execute_isolated_proposals(mock_generator, count=3)

    assert len(results) == 3
    assert "proposal_a" in results
    assert "proposal_b" in results
    assert "proposal_c" in results

    # Ensure all three executed with different titles and concepts
    titles = [r["title"] for r in results.values()]
    assert len(set(titles)) == 3
    assert titles == ["Story proposal_a", "Story proposal_b", "Story proposal_c"]


def test_verify_no_cross_proposal_contamination():
    """Test detection of mutual context leaks between proposals (Step 10)."""
    clean_proposals = {
        "proposal_a": {
            "title": "銀河の覇王",
            "synopsis": "宇宙空間での艦隊戦と政治劇を描くスペースオペラ。",
        },
        "proposal_b": {
            "title": "深海の秘宝",
            "synopsis": "海底都市に眠る古代遺物を巡るアドベンチャー活劇。",
        },
    }
    clean_res = verify_no_cross_proposal_contamination(clean_proposals)
    assert clean_res.passed is True
    assert len(clean_res.violations) == 0

    # Contaminated with explicit leak phrase
    phrase_leak_proposals = {
        "proposal_a": {
            "title": "銀河の覇王",
            "synopsis": "A案では宇宙空間での艦隊戦を描くが他案よりも規模が大きい。",
        },
        "proposal_b": {
            "title": "深海の秘宝",
            "synopsis": "海底都市に眠る古代遺物を探検する。",
        },
    }
    leak_res1 = verify_no_cross_proposal_contamination(phrase_leak_proposals)
    assert leak_res1.passed is False
    assert any("cross_proposal_leak_pattern" in v.violation_type for v in leak_res1.violations)

    # Contaminated with title of another proposal
    cross_title_proposals = {
        "proposal_a": {
            "title": "銀河の覇王",
            "synopsis": "宇宙空間での艦隊戦を描く。",
        },
        "proposal_b": {
            "title": "深海の秘宝",
            "synopsis": "海底都市だけでなく銀河の覇王の要素も取り入れる。",
        },
    }
    leak_res2 = verify_no_cross_proposal_contamination(cross_title_proposals)
    assert leak_res2.passed is False
    assert any("cross_proposal_contamination" in v.violation_type for v in leak_res2.violations)


def test_strict_blind_routing():
    """Test strict blind routing failure upon unscrubbed forbidden content (Step 11)."""
    schema = IsolationSchema.from_legacy(
        forbidden_agents=["planning_b"],
        blocked_keys={"secret_plot"},
    )
    schema.strict_blind_routing = True

    gate = BlindReviewGate(
        forbidden_agents=["planning_b"],
        blocked_keys=["secret_plot"],
        schema=schema,
    )

    # Clean payload containing blocked key (gets scrubbed properly, so verification passes)
    payload = {
        "public_critique": "とても良いプロットです。",
        "secret_plot": "禁断のネタバレ",
    }
    scrubbed = gate.scrub_payload(payload)
    assert scrubbed["secret_plot"].startswith("<BLOCKED:")

    # Create a broken schema where a key is marked as forbidden but not scrubbed, or simulate leaked marker
    # In strict mode, if verify_isolation fails, ValueError must be raised
    class DefectiveGate(BlindReviewGate):
        def _deep_scrub(self, obj, path=""):
            # Intentionally leak marker into public field
            return {"public_critique": "<BLOCKED:leak>", "normal_field": "ok"}

    defective_gate = DefectiveGate(
        forbidden_agents=["planning_b"],
        schema=schema,
    )
    with pytest.raises(ValueError, match="Strict blind routing failed"):
        defective_gate.scrub_payload(payload)
