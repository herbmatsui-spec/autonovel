"""Property-based tests for Grammar Balancer using Hypothesis."""

from hypothesis import given, strategies as st
from src.narrative_balancer.grammar.balancer import GrammarNarrativeBalancer
from src.narrative_balancer.models import Beat, BeatType


@given(st.lists(st.sampled_from(list(BeatType)), min_size=5, max_size=30))
def test_grammar_balancer_idempotency(beat_types):
    beats = [Beat(episode=i + 1, beat_type=bt) for i, bt in enumerate(beat_types)]
    balancer = GrammarNarrativeBalancer()

    run1 = balancer.balance(beats)
    run2 = balancer.balance(run1)

    assert len(run1) == len(run2)
    for b1, b2 in zip(run1, run2):
        assert b1.beat_type == b2.beat_type
        assert b1.tension == b2.tension
