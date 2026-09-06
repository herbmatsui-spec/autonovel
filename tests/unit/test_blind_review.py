"""Unit tests for BlindReviewGate."""

import pytest
from src.services.blind_review import (
    BlindReviewGate,
    BLOCKED_TOKEN_FMT,
    HASH_TOKEN_FMT,
    IsolationSchema,
    VerificationResult,
    IsolationViolation,
)


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

    # --- deterministic_hash mode tests ---

    def test_deterministic_hash_mode_key_order_independent(self):
        """deterministic_hash mode produces same hash regardless of key order."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="deterministic_hash")
        o1 = gate.scrub_payload({"secret_data": {"z": 1, "a": 2}})
        o2 = gate.scrub_payload({"secret_data": {"a": 2, "z": 1}})
        assert o1 == o2
        assert o1["secret_data"].startswith("<HASH:")
        assert o1["secret_data"].endswith(">")

    def test_deterministic_hash_mode_set_order_independent(self):
        """deterministic_hash mode produces same hash regardless of set iteration order."""
        gate = BlindReviewGate(forbidden_agents=["tags"], mode="deterministic_hash")
        o1 = gate.scrub_payload({"tags_set": {"c", "a", "b"}})
        o2 = gate.scrub_payload({"tags_set": {"a", "b", "c"}})
        assert o1 == o2
        assert o1["tags_set"].startswith("<HASH:")

    def test_hash_mode_with_deterministic_flag(self):
        """hash mode with deterministic=True equals deterministic_hash mode."""
        gate1 = BlindReviewGate(forbidden_agents=["x"], mode="deterministic_hash")
        gate2 = BlindReviewGate(forbidden_agents=["x"], mode="hash", deterministic=True)
        o1 = gate1.scrub_payload({"x_val": {"b": 1, "a": 2}})
        o2 = gate2.scrub_payload({"x_val": {"b": 1, "a": 2}})
        assert o1 == o2

    def test_hash_mode_default_backward_compat(self):
        """Default hash mode (deterministic=False) may produce different hashes for key order."""
        gate = BlindReviewGate(forbidden_agents=["x"], mode="hash")
        o1 = gate.scrub_payload({"x_val": {"z": 1, "a": 2}})
        o2 = gate.scrub_payload({"x_val": {"a": 2, "z": 1}})
        # Backward compat: key order may affect hash (not guaranteed to differ, but allowed)
        assert o1["x_val"].startswith("<HASH:")
        assert o2["x_val"].startswith("<HASH:")

    def test_deterministic_hash_nested_structures(self):
        """deterministic_hash works with nested dicts and sets (lists preserve order)."""
        gate = BlindReviewGate(forbidden_agents=["data"], mode="deterministic_hash")
        payload = {
            "data_payload": {
                "nested": {"z": 1, "a": 2},
                "items": [{"b": 1}, {"a": 2}],  # list order preserved
                "tags": {"c", "a", "b"},  # set order independent
            }
        }
        o1 = gate.scrub_payload(payload)
        o2 = gate.scrub_payload({
            "data_payload": {
                "nested": {"a": 2, "z": 1},  # dict key order independent
                "items": [{"b": 1}, {"a": 2}],  # same list order
                "tags": {"a", "b", "c"},  # set order independent
            }
        })
        assert o1 == o2

    def test_deterministic_mode_rejected_for_scrub(self):
        """deterministic flag only applies to hash modes; scrub mode ignores it."""
        gate = BlindReviewGate(forbidden_agents=["x"], mode="scrub", deterministic=True)
        o1 = gate.scrub_payload({"x_val": "secret"})
        o2 = gate.scrub_payload({"x_val": "secret"})
        assert o1 == o2
        assert o1["x_val"] == "<BLOCKED:x>"

    def test_invalid_mode_rejected(self):
        """Invalid mode raises ValueError."""
        with pytest.raises(ValueError):
            BlindReviewGate(forbidden_agents=["x"], mode="invalid_mode")

    # --- IsolationSchema & verify_isolation tests ---

    def test_isolation_schema_from_legacy(self):
        """IsolationSchema.from_legacy creates correct rules from agents/keys."""
        schema = IsolationSchema.from_legacy(
            forbidden_agents=["planning", "plot"],
            blocked_keys={"proposal_b"},
        )
        assert "planning" in schema.exact_keys
        assert "plot" in schema.exact_keys
        assert "proposal_b" in schema.exact_keys
        assert "planning_" in schema.prefix_rules
        assert "_planning" in schema.suffix_rules
        assert "plot_" in schema.prefix_rules
        assert "_plot" in schema.suffix_rules

    def test_isolation_schema_is_blocked_exact(self):
        """Exact key matching works."""
        schema = IsolationSchema(exact_keys={"secret_key", "forbidden"})
        assert schema.is_blocked("secret_key") is True
        assert schema.is_blocked("forbidden") is True
        assert schema.is_blocked("allowed") is False

    def test_isolation_schema_is_blocked_prefix(self):
        """Prefix matching works."""
        schema = IsolationSchema(prefix_rules=["secret_", "internal_"])
        assert schema.is_blocked("secret_data") is True
        assert schema.is_blocked("internal_config") is True
        assert schema.is_blocked("public_data") is False

    def test_isolation_schema_is_blocked_suffix(self):
        """Suffix matching works."""
        schema = IsolationSchema(suffix_rules=["_secret", "_internal"])
        assert schema.is_blocked("data_secret") is True
        assert schema.is_blocked("config_internal") is True
        assert schema.is_blocked("data_public") is False

    def test_isolation_schema_is_blocked_nested_path(self):
        """Nested path matching works."""
        schema = IsolationSchema(nested_paths=["outer.inner.forbidden"])
        assert schema.is_blocked("forbidden", "outer.inner") is True
        assert schema.is_blocked("forbidden", "other.inner") is False
        assert schema.is_blocked("allowed", "outer.inner") is False

    def test_isolation_schema_is_blocked_regex(self):
        """Regex matching works."""
        schema = IsolationSchema()
        schema.add_regex(r"secret_\d+")
        assert schema.is_blocked("secret_123") is True
        assert schema.is_blocked("secret_abc") is False

    def test_verify_isolation_clean_payload(self):
        """verify_isolation passes for properly scrubbed payload."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="scrub")
        payload = {"public": "data", "secret_value": "<BLOCKED:secret>"}
        result = gate.verify_isolation(payload)
        assert result.passed is True
        assert len(result.violations) == 0

    def test_verify_isolation_detects_marker_leak(self):
        """verify_isolation detects leaked scrub markers in non-meta fields."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="scrub")
        # Simulate a leaked marker (should not happen in normal operation)
        payload = {"leaked": "<BLOCKED:secret>", "public": "ok"}
        result = gate.verify_isolation(payload)
        assert result.passed is False
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "marker_leak"
        assert "leaked" in result.violations[0].path

    def test_verify_isolation_allows_markers_in_blind_meta(self):
        """verify_isolation allows markers in _blind_meta (cross-round metadata)."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="scrub")
        payload = {
            "_blind_meta": {"round_id": "r1", "marker": "<BLOCKED:secret>"},
            "public": "ok",
        }
        result = gate.verify_isolation(payload)
        assert result.passed is True

    def test_verify_isolation_detects_unscrubbed_key(self):
        """verify_isolation detects blocked keys that weren't scrubbed."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="scrub")
        # Manually create payload with unscrubbed blocked key
        payload = {"secret_data": "should_be_scrubbed", "public": "ok"}
        result = gate.verify_isolation(payload)
        assert result.passed is False
        assert len(result.violations) == 1
        assert result.violations[0].violation_type == "unscrubbed_key"

    def test_verify_isolation_with_hash_mode(self):
        """verify_isolation works with hash mode markers too."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="hash")
        payload = {"public": "data", "secret_value": "<HASH:abc12345>"}
        result = gate.verify_isolation(payload)
        assert result.passed is True

    def test_verify_isolation_detects_hash_marker_leak(self):
        """verify_isolation detects leaked hash markers."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="hash")
        payload = {"leaked": "<HASH:abc12345>", "public": "ok"}
        result = gate.verify_isolation(payload)
        assert result.passed is False
        assert result.violations[0].violation_type == "marker_leak"

    def test_verify_isolation_nested_structure(self):
        """verify_isolation works with nested dicts and lists."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="scrub")
        payload = {
            "outer": {
                "inner": {"secret_nested": "<BLOCKED:secret>"},
                "list": [{"secret_item": "<BLOCKED:secret>"}],
            },
            "public": "ok",
        }
        result = gate.verify_isolation(payload)
        assert result.passed is True

    def test_verify_isolation_detects_nested_leak(self):
        """verify_isolation detects leaks in nested structures."""
        gate = BlindReviewGate(forbidden_agents=["secret"], mode="scrub")
        payload = {
            "outer": {
                "leaked": "<BLOCKED:secret>",  # Not in _blind_meta
            },
        }
        result = gate.verify_isolation(payload)
        assert result.passed is False
        assert result.violations[0].path == "outer.leaked"

    def test_isolation_schema_fluent_api(self):
        """IsolationSchema fluent API works."""
        schema = (IsolationSchema()
                  .add_exact_key("exact")
                  .add_prefix("pre_")
                  .add_suffix("_suf")
                  .add_nested_path("path.to.block")
                  .add_regex(r"regex_\d+"))
        assert "exact" in schema.exact_keys
        assert "pre_" in schema.prefix_rules
        assert "_suf" in schema.suffix_rules
        assert "path.to.block" in schema.nested_paths
        assert len(schema.regex_patterns) == 1

    def test_custom_schema_overrides_legacy(self):
        """Custom schema passed to BlindReviewGate overrides legacy rules."""
        custom_schema = IsolationSchema(exact_keys={"custom_only"})
        gate = BlindReviewGate(
            forbidden_agents=["legacy_agent"],
            blocked_keys=["legacy_key"],
            schema=custom_schema,
        )
        assert gate.schema.exact_keys == {"custom_only"}
        # Legacy rules should not be present
        assert "legacy_agent" not in gate.schema.exact_keys
        assert "legacy_key" not in gate.schema.exact_keys

    # --- Cross-round contamination detection tests ---

    def test_cross_round_contamination_detected_and_rescrubbed(self):
        """Markers from previous round outside _blind_meta are detected and re-scrubbed."""
        gate = BlindReviewGate(
            forbidden_agents=["secret"],
            mode="scrub",
            current_round_id="round_2",
        )
        # Simulate payload with marker from round 1 leaked into public field
        payload = {
            "public_field": "<BLOCKED:secret>",  # Contamination!
            "secret_data": "new_secret",
        }
        result = gate.scrub_payload(payload)
        # Contamination should be re-scrubbed
        assert result["public_field"] == "<BLOCKED:cross_round_contamination>"
        # Normal blocked key should still be scrubbed
        assert result["secret_data"] == "<BLOCKED:secret>"
        assert gate.blocked_count == 2

    def test_cross_round_contamination_hash_mode(self):
        """Cross-round contamination detection works in hash mode too."""
        gate = BlindReviewGate(
            forbidden_agents=["secret"],
            mode="hash",
            current_round_id="round_2",
        )
        payload = {
            "public_field": "<HASH:abc12345>",  # Contamination from previous round
        }
        result = gate.scrub_payload(payload)
        assert result["public_field"].startswith("<HASH:")
        assert result["public_field"] != "<HASH:abc12345>"  # Re-hashed
        assert gate.blocked_count == 1

    def test_no_contamination_without_current_round_id(self):
        """Without current_round_id, markers in public fields are not re-scrubbed (backward compat)."""
        gate = BlindReviewGate(
            forbidden_agents=["secret"],
            mode="scrub",
            # No current_round_id
        )
        payload = {
            "public_field": "<BLOCKED:secret>",  # Would be contamination but no round_id
        }
        result = gate.scrub_payload(payload)
        # Without round_id, marker passes through (but verify_isolation would catch it)
        assert result["public_field"] == "<BLOCKED:secret>"
        assert gate.blocked_count == 0

    def test_blind_meta_markers_preserved(self):
        """Markers in _blind_meta are preserved (not treated as contamination)."""
        gate = BlindReviewGate(
            forbidden_agents=["secret"],
            mode="scrub",
            current_round_id="round_2",
        )
        payload = {
            "_blind_meta": {
                "round_id": "round_1",
                "old_marker": "<BLOCKED:secret>",  # This is OK in metadata
            },
            "secret_data": "new_secret",
        }
        result = gate.scrub_payload(payload)
        # Metadata markers preserved
        assert result["_blind_meta"]["old_marker"] == "<BLOCKED:secret>"
        # Normal blocked key scrubbed
        assert result["secret_data"] == "<BLOCKED:secret>"
        assert gate.blocked_count == 1

    def test_config_hash_property(self):
        """config_hash property returns deterministic hash of gate configuration."""
        gate1 = BlindReviewGate(
            forbidden_agents=["a", "b"],
            mode="deterministic_hash",
            blocked_keys=["key1"],
        )
        gate2 = BlindReviewGate(
            forbidden_agents=["b", "a"],  # Different order
            mode="deterministic_hash",
            blocked_keys=["key1"],
        )
        gate3 = BlindReviewGate(
            forbidden_agents=["a", "b"],
            mode="scrub",  # Different mode
            blocked_keys=["key1"],
        )
        assert gate1.config_hash == gate2.config_hash  # Order independent
        assert gate1.config_hash != gate3.config_hash  # Mode difference changes hash
        assert len(gate1.config_hash) == 16