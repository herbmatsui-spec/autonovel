"""Unit tests for BlindReviewGate."""

import pytest
from src.services.blind_review import BlindReviewGate, BLOCKED_TOKEN_FMT, HASH_TOKEN_FMT


class TestBlindReviewGate:
    def test_basic_scrub(self):
        gate = BlindReviewGate(forbidden_agents=["planning"])
        payload = {"planning_output_a": "secret", "draft_text": "public"}
        out = gate.scrub_payload(payload)
        assert out["planning_output_a"] == BLOCKED_TOKEN_FMT.format(source="planning")
        assert out["draft_text"] == "public"
        assert gate.blocked_count == 1

    def test_nested_scrub(self):
        gate = BlindReviewGate(forbidden_agents=["plot"])
        payload = {"outer": {"plot_tree": {"nodes": ["x"]}, "meta": {"plot_summary": "y"}}, "ok": 1}
        out = gate.scrub_payload(payload)
        assert out["outer"]["plot_tree"] == BLOCKED_TOKEN_FMT.format(source="plot")
        assert out["outer"]["meta"]["plot_summary"] == BLOCKED_TOKEN_FMT.format(source="plot")
        assert out["ok"] == 1
        assert gate.blocked_count == 2

    def test_hash_mode_deterministic(self):
        gate = BlindReviewGate(forbidden_agents=["bible"], mode="hash")
        o1 = gate.scrub_payload({"bible_snapshot": "secret text"})
        o2 = gate.scrub_payload({"bible_snapshot": "secret text"})
        assert o1 == o2
        assert o1["bible_snapshot"].startswith("<HASH:")
        assert o1["bible_snapshot"].endswith(">")

    def test_hash_mode_different_inputs(self):
        gate = BlindReviewGate(forbidden_agents=["bible"], mode="hash")
        o1 = gate.scrub_payload({"bible_snapshot": "secret text"})
        o2 = gate.scrub_payload({"bible_snapshot": "different text"})
        assert o1 != o2

    def test_is_blocked(self):
        gate = BlindReviewGate(forbidden_agents=["other"])
        assert gate.is_blocked("other", "self") is True
        assert gate.is_blocked("self", "self") is False

    def test_empty_payload(self):
        gate = BlindReviewGate(forbidden_agents=["x"])
        assert gate.scrub_payload(None) == {}
        assert gate.scrub_payload({}) == {}

    def test_explicit_blocked_keys(self):
        gate = BlindReviewGate(forbidden_agents=["planning"], blocked_keys=["proposal_b"])
        payload = {"proposal_b": "x", "proposal_a": "y"}
        out = gate.scrub_payload(payload)
        assert "BLOCKED:" in out["proposal_b"]
        assert out["proposal_a"] == "y"

    def test_json_roundtrip(self):
        import json
        gate = BlindReviewGate(forbidden_agents=["a"])
        payload = {"a_x": {"a_y": [1, 2, 3]}}
        roundtrip = json.loads(json.dumps(gate.scrub_payload(payload), ensure_ascii=False))
        assert "BLOCKED:a" in str(roundtrip["a_x"])

    def test_tuple_and_list_deep_scrub(self):
        gate = BlindReviewGate(forbidden_agents=["b"])
        # Only dict keys are scrubbed; tuple/list values pass through
        payload = {"items": [{"b_thing": 1, "ok": 2}, ("b_x", "y")]}
        out = gate.scrub_payload(payload)
        assert out["items"][0]["b_thing"] == BLOCKED_TOKEN_FMT.format(source="b")
        assert out["items"][0]["ok"] == 2
        # Tuple values are NOT scrubbed (only dict keys)
        assert out["items"][1] == ("b_x", "y")

    def test_performance(self):
        import time
        gate = BlindReviewGate(forbidden_agents=["big"])
        big = {"data": [{"big_field": "x" * 100, "ok": "y"} for _ in range(100)]}
        t0 = time.perf_counter()
        _ = gate.scrub_payload(big)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 100, f"too slow: {elapsed_ms}ms"

    def test_empty_forbidden_agents_rejected(self):
        with pytest.raises(ValueError):
            BlindReviewGate(forbidden_agents=[])