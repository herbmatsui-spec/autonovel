from src.services.blind_review import BlindReviewGate

def test_blind_review_gate_isolation():
    gate = BlindReviewGate(forbidden_agents=["agent_a"])
    payload = {"agent_a_output": "秘密の計画", "public_data": "公開情報"}
    scrubbed = gate.scrub_payload(payload)
    assert "秘密の計画" not in str(scrubbed)
    assert "public_data" in str(scrubbed)
