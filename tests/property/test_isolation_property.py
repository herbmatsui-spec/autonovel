"""Property-based tests for blind review isolation guarantees.

Uses Hypothesis to verify that isolation properties hold for arbitrary payloads.
"""

import pytest
from hypothesis import given, settings, strategies as st
from src.services.blind_review import (
    BlindReviewGate,
    IsolationSchema,
    VerificationResult,
)


# Strategy for arbitrary JSON-serializable values
json_value = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | st.text(),
    lambda children: st.lists(children, max_size=5) | st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
    max_leaves=20,
)


# Strategy for forbidden agent names
agent_name = st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_")).filter(lambda s: len(s) > 0)


@settings(max_examples=200, deadline=None)
@given(
    payload=json_value,
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=3, unique=True),
    mode=st.sampled_from(["scrub", "hash", "deterministic_hash"]),
)
def test_isolation_never_leaks_markers(payload, forbidden_agents, mode):
    """Property: After scrub_payload, verify_isolation always passes.

    This is the core isolation guarantee: no matter what payload you start with,
    after scrubbing with a gate, the result should pass verification.
    """
    # Build blocked_keys from agent names
    blocked_keys = [f"{a}_data" for a in forbidden_agents]

    gate = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode=mode,
        blocked_keys=blocked_keys,
    )

    # Inject some blocked keys into payload to ensure they get scrubbed
    if isinstance(payload, dict):
        tainted = dict(payload)
        for k in blocked_keys:
            tainted[k] = "SECRET_VALUE"
    else:
        tainted = {"data": payload}
        for k in blocked_keys:
            tainted[k] = "SECRET_VALUE"

    scrubbed = gate.scrub_payload(tainted)
    result = gate.verify_isolation(scrubbed)

    assert result.passed, f"Isolation violated: {result.violations}"


@settings(max_examples=100, deadline=None)
@given(
    payload=json_value,
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=3, unique=True),
)
def test_blocked_keys_always_scrubbed(payload, forbidden_agents):
    """Property: Explicitly blocked keys are always scrubbed (marker present)."""
    blocked_keys = [f"{a}_secret" for a in forbidden_agents]

    gate = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="scrub",
        blocked_keys=blocked_keys,
    )

    # Create payload with all blocked keys present
    if isinstance(payload, dict):
        tainted = dict(payload)
    else:
        tainted = {"payload": payload}

    for k in blocked_keys:
        tainted[k] = "SHOULD_BE_SCRUBBED"

    scrubbed = gate.scrub_payload(tainted)

    # Every blocked key must have a marker
    for k in blocked_keys:
        assert k in scrubbed, f"Blocked key {k} missing from scrubbed payload"
        assert scrubbed[k].startswith("<BLOCKED:"), f"Key {k} not properly scrubbed: {scrubbed[k]}"


@settings(max_examples=100, deadline=None)
@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=10),
        json_value,
        min_size=1,
        max_size=5,
    ),
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=3, unique=True),
)
def test_deterministic_hash_key_order_independent(payload, forbidden_agents):
    """Property: deterministic_hash mode produces identical output regardless of key order."""
    blocked_keys = [f"{a}_data" for a in forbidden_agents]

    gate1 = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="deterministic_hash",
        blocked_keys=blocked_keys,
    )
    gate2 = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="deterministic_hash",
        blocked_keys=blocked_keys,
    )

    # Create two payloads with same data but different key orders
    # (dict order doesn't matter in Python 3.7+, but we test nested structures)
    tainted1 = dict(payload)
    tainted2 = dict(reversed(list(payload.items())))
    for k in blocked_keys:
        tainted1[k] = "SECRET"
        tainted2[k] = "SECRET"

    out1 = gate1.scrub_payload(tainted1)
    out2 = gate2.scrub_payload(tainted2)

    # Outputs should be identical
    assert out1 == out2, "deterministic_hash should be key-order independent"


@settings(max_examples=100, deadline=None)
@given(
    items=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5, unique=True),
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=2, unique=True),
)
def test_deterministic_hash_set_order_independent(items, forbidden_agents):
    """Property: deterministic_hash handles sets with different iteration orders."""
    blocked_keys = [f"{a}_tags" for a in forbidden_agents]

    gate1 = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="deterministic_hash",
        blocked_keys=blocked_keys,
    )
    gate2 = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="deterministic_hash",
        blocked_keys=blocked_keys,
    )

    # Same set, different iteration order (achieved by different construction)
    set1 = set(items)
    set2 = set(reversed(items))

    tainted1 = {blocked_keys[0]: set1}
    tainted2 = {blocked_keys[0]: set2}

    out1 = gate1.scrub_payload(tainted1)
    out2 = gate2.scrub_payload(tainted2)

    assert out1 == out2, "deterministic_hash should be set-order independent"


@settings(max_examples=100, deadline=None)
@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=10),
        json_value,
        min_size=1,
        max_size=5,
    ),
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=3, unique=True),
)
def test_isolation_schema_exact_match(payload, forbidden_agents):
    """Property: IsolationSchema exact key matching works correctly."""
    schema = IsolationSchema(exact_keys={"forbidden_key", "secret_data"})

    # Keys in exact_keys should be blocked
    assert schema.is_blocked("forbidden_key") is True
    assert schema.is_blocked("secret_data") is True

    # Similar but not exact keys should not be blocked
    assert schema.is_blocked("forbidden_key_extra") is False
    assert schema.is_blocked("extra_secret_data") is False
    assert schema.is_blocked("allowed_key") is False


def test_isolation_schema_prefix_match():
    """IsolationSchema prefix matching works correctly."""
    for prefix in ["secret", "internal", "private", "hidden"]:
        schema = IsolationSchema(prefix_rules=[f"{prefix}_"])
        assert schema.is_blocked(f"{prefix}_data") is True
        assert schema.is_blocked(f"{prefix}_secret") is True
        assert schema.is_blocked(f"{prefix}x_data") is False
        assert schema.is_blocked(f"other_{prefix}_data") is False


def test_isolation_schema_suffix_match():
    """IsolationSchema suffix matching works correctly."""
    for suffix in ["secret", "internal", "private", "hidden"]:
        schema = IsolationSchema(suffix_rules=[f"_{suffix}"])
        assert schema.is_blocked(f"data_{suffix}") is True
        assert schema.is_blocked(f"secret_{suffix}") is True
        assert schema.is_blocked(f"data_{suffix}x") is False
        assert schema.is_blocked(f"data_{suffix}_extra") is False


@settings(max_examples=50, deadline=None)
@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=10),
        json_value,
        min_size=1,
        max_size=3,
    ),
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=2, unique=True),
)
def test_verify_isolation_idempotent(payload, forbidden_agents):
    """Property: verify_isolation is idempotent on already-scrubbed payloads."""
    blocked_keys = [f"{a}_data" for a in forbidden_agents]

    gate = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="scrub",
        blocked_keys=blocked_keys,
    )

    if isinstance(payload, dict):
        tainted = dict(payload)
    else:
        tainted = {"data": payload}

    for k in blocked_keys:
        tainted[k] = "SECRET"

    scrubbed = gate.scrub_payload(tainted)
    result1 = gate.verify_isolation(scrubbed)
    result2 = gate.verify_isolation(scrubbed)

    assert result1.passed == result2.passed
    assert len(result1.violations) == len(result2.violations)


@settings(max_examples=100, deadline=None)
@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=10),
        json_value,
        min_size=1,
        max_size=5,
    ),
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=3, unique=True),
)
def test_cross_round_contamination_rejected(payload, forbidden_agents):
    """Property: Cross-round contamination is detected when current_round_id is set."""
    blocked_keys = [f"{a}_data" for a in forbidden_agents]

    gate = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="scrub",
        blocked_keys=blocked_keys,
        current_round_id="round_2",
    )

    if isinstance(payload, dict):
        tainted = dict(payload)
    else:
        tainted = {"data": payload}

    # Inject a marker from "previous round" into a public field
    tainted["leaked_from_round_1"] = "<BLOCKED:some_agent>"

    for k in blocked_keys:
        tainted[k] = "SECRET"

    scrubbed = gate.scrub_payload(tainted)

    # The leaked marker should be re-scrubbed
    assert scrubbed["leaked_from_round_1"] == "<BLOCKED:cross_round_contamination>"
    # Normal blocked keys should still be scrubbed (lowercased agent name)
    for k in blocked_keys:
        expected_agent = forbidden_agents[0].lower()
        assert scrubbed[k] == f"<BLOCKED:{expected_agent}>"


@settings(max_examples=50, deadline=None)
@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=10),
        json_value,
        min_size=1,
        max_size=3,
    ),
    forbidden_agents=st.lists(agent_name, min_size=1, max_size=2, unique=True),
)
def test_blind_meta_markers_preserved(payload, forbidden_agents):
    """Property: Markers in _blind_meta are always preserved."""
    blocked_keys = [f"{a}_data" for a in forbidden_agents]

    gate = BlindReviewGate(
        forbidden_agents=forbidden_agents,
        mode="scrub",
        blocked_keys=blocked_keys,
        current_round_id="round_2",
    )

    if isinstance(payload, dict):
        tainted = dict(payload)
    else:
        tainted = {"data": payload}

    tainted["_blind_meta"] = {
        "round_id": "round_1",
        "old_marker": "<BLOCKED:previous_agent>",
        "nested": {"marker": "<HASH:abc12345>"},
    }

    for k in blocked_keys:
        tainted[k] = "SECRET"

    scrubbed = gate.scrub_payload(tainted)

    # All markers in _blind_meta should be preserved exactly
    assert scrubbed["_blind_meta"]["old_marker"] == "<BLOCKED:previous_agent>"
    assert scrubbed["_blind_meta"]["nested"]["marker"] == "<HASH:abc12345>"
    # Normal blocked keys still scrubbed (lowercased agent name)
    for k in blocked_keys:
        expected_agent = forbidden_agents[0].lower()
        assert scrubbed[k] == f"<BLOCKED:{expected_agent}>"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])