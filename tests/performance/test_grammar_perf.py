"""Performance test for Grammar Balancer."""

import pytest
from benchmarks.benchmark_grammar import benchmark_grammar


@pytest.mark.perf
def test_grammar_performance():
    res = benchmark_grammar(iterations=5)
    # Target < 100ms
    assert res["avg_ms"] < 100.0
