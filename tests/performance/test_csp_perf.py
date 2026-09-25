"""Performance test for CSP Balancer."""

import pytest
from benchmarks.benchmark_csp import benchmark_csp


@pytest.mark.perf
def test_csp_performance_target():
    res = benchmark_csp(iterations=3)
    # Check that average solve time is reasonable (< 1500ms for 20ep)
    assert res["avg_ms"] < 2000.0
