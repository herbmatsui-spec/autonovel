"""Unit tests for ReviewSession and ReviewRound."""

import pytest
from datetime import datetime, timedelta
from src.domain.entities.review_session import ReviewRound, ReviewSession


class TestReviewRound:
    def test_score_delta_no_previous(self):
        round_ = ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0, "plan_b": 78.0},
            plan_critiques={},
            gate_config_hash="abc123",
        )
        deltas = round_.score_delta(None)
        assert deltas == {"plan_a": 85.0, "plan_b": 78.0}

    def test_score_delta_with_previous(self):
        prev = ReviewRound(
            round_number=0,
            timestamp=datetime.now() - timedelta(minutes=5),
            plan_scores={"plan_a": 80.0, "plan_b": 75.0},
            plan_critiques={},
            gate_config_hash="abc123",
        )
        curr = ReviewRound(
            round_number=1,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 83.0, "plan_b": 76.0},
            plan_critiques={},
            gate_config_hash="abc123",
        )
        deltas = curr.score_delta(prev)
        assert deltas == {"plan_a": 3.0, "plan_b": 1.0}

    def test_score_delta_new_plan(self):
        prev = ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 80.0},
            plan_critiques={},
            gate_config_hash="abc123",
        )
        curr = ReviewRound(
            round_number=1,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 83.0, "plan_b": 90.0},
            plan_critiques={},
            gate_config_hash="abc123",
        )
        deltas = curr.score_delta(prev)
        assert deltas == {"plan_a": 3.0, "plan_b": 90.0}


class TestReviewSession:
    def test_add_round_updates_timestamp(self):
        session = ReviewSession(request_id="req_123")
        initial_updated = session.updated_at
        round_ = ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0},
            plan_critiques={},
            gate_config_hash="abc123",
        )
        session.add_round(round_)
        assert session.updated_at > initial_updated
        assert len(session.rounds) == 1

    def test_latest_round(self):
        session = ReviewSession(request_id="req_123")
        assert session.latest_round() is None
        round_ = ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0},
            plan_critiques={},
            gate_config_hash="abc123",
        )
        session.add_round(round_)
        assert session.latest_round() is round_

    def test_should_continue_review_min_rounds(self):
        session = ReviewSession(request_id="req_123")
        # min_rounds=1, 0 rounds -> should continue
        assert session.should_continue_review(min_rounds=1) is True

    def test_should_continue_review_max_rounds(self):
        session = ReviewSession(request_id="req_123")
        for i in range(3):
            session.add_round(ReviewRound(
                round_number=i,
                timestamp=datetime.now(),
                plan_scores={"plan_a": 85.0},
                plan_critiques={},
                gate_config_hash="abc123",
            ))
        # max_rounds=3, 3 rounds -> should NOT continue
        assert session.should_continue_review(max_rounds=3) is False

    def test_should_continue_review_converged(self):
        session = ReviewSession(request_id="req_123")
        # Round 0
        session.add_round(ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0, "plan_b": 80.0},
            plan_critiques={},
            gate_config_hash="abc123",
        ))
        # Round 1 - small delta (< 2.0)
        session.add_round(ReviewRound(
            round_number=1,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 86.0, "plan_b": 81.0},
            plan_critiques={},
            gate_config_hash="abc123",
        ))
        # Should converge (all deltas < 2.0)
        assert session.should_continue_review(max_rounds=3, score_delta_threshold=2.0) is False

    def test_should_continue_review_not_converged(self):
        session = ReviewSession(request_id="req_123")
        # Round 0
        session.add_round(ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0, "plan_b": 80.0},
            plan_critiques={},
            gate_config_hash="abc123",
        ))
        # Round 1 - large delta (>= 2.0)
        session.add_round(ReviewRound(
            round_number=1,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 88.0, "plan_b": 81.0},
            plan_critiques={},
            gate_config_hash="abc123",
        ))
        # Should NOT converge (plan_a delta = 3.0 >= 2.0)
        assert session.should_continue_review(max_rounds=3, score_delta_threshold=2.0) is True

    def test_get_convergence_report_insufficient_data(self):
        session = ReviewSession(request_id="req_123")
        session.add_round(ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0},
            plan_critiques={},
            gate_config_hash="abc123",
        ))
        report = session.get_convergence_report()
        assert report["status"] == "insufficient_data"
        assert report["rounds"] == 1

    def test_get_convergence_report(self):
        session = ReviewSession(request_id="req_123")
        session.add_round(ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0, "plan_b": 80.0},
            plan_critiques={},
            gate_config_hash="abc123",
        ))
        session.add_round(ReviewRound(
            round_number=1,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 88.0, "plan_b": 81.0},
            plan_critiques={},
            gate_config_hash="abc123",
        ))
        report = session.get_convergence_report()
        assert report["total_rounds"] == 2
        assert "plan_a" in report["plan_trajectories"]
        assert "plan_b" in report["plan_trajectories"]
        assert report["plan_trajectories"]["plan_a"][0]["delta"] == 3.0
        assert report["plan_trajectories"]["plan_b"][0]["delta"] == 1.0

    def test_roundtrip_serialization(self):
        session = ReviewSession(
            session_id="review_test123",
            request_id="req_123",
            gate_forbidden_agents=["agent_a", "agent_b"],
            gate_mode="hash",
            gate_blocked_keys=["key1", "key2"],
        )
        session.add_round(ReviewRound(
            round_number=0,
            timestamp=datetime.now(),
            plan_scores={"plan_a": 85.0, "plan_b": 78.0},
            plan_critiques={"plan_a": {"clarity": "high"}},
            gate_config_hash="abc123",
            converged=False,
            feedback_hash="def456",
        ))

        data = session.to_dict()
        restored = ReviewSession.from_dict(data)

        assert restored.session_id == session.session_id
        assert restored.request_id == session.request_id
        assert restored.gate_forbidden_agents == session.gate_forbidden_agents
        assert restored.gate_mode == session.gate_mode
        assert restored.gate_blocked_keys == session.gate_blocked_keys
        assert len(restored.rounds) == 1
        assert restored.rounds[0].round_number == 0
        assert restored.rounds[0].plan_scores == session.rounds[0].plan_scores
        assert restored.rounds[0].gate_config_hash == session.rounds[0].gate_config_hash
        assert restored.rounds[0].feedback_hash == session.rounds[0].feedback_hash

    def test_compute_gate_config_hash_deterministic(self):
        hash1 = ReviewSession._compute_gate_config_hash(
            ["agent_b", "agent_a"], "scrub", ["key2", "key1"]
        )
        hash2 = ReviewSession._compute_gate_config_hash(
            ["agent_a", "agent_b"], "scrub", ["key1", "key2"]
        )
        assert hash1 == hash2  # 順不同でも同じハッシュ

    def test_compute_gate_config_hash_different_inputs(self):
        hash1 = ReviewSession._compute_gate_config_hash(
            ["agent_a"], "scrub", ["key1"]
        )
        hash2 = ReviewSession._compute_gate_config_hash(
            ["agent_b"], "scrub", ["key1"]
        )
        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])