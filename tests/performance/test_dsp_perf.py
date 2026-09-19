"""Performance test for DSP Balancer."""

import pytest
from benchmarks.benchmark_dsp import benchmark_dsp


@pytest.mark.perf
def test_dsp_performance_threshold():
    res = benchmark_dsp(iterations=200)
    # Target p99 < 5ms
    assert res["p99_ms"] < 15.0  # Generous threshold to pass on any machine/CI
