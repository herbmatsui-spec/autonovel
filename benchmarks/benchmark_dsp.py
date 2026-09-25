"""Performance benchmark for DSP Balancer."""

import time
import numpy as np
from src.narrative_balancer.dsp.balancer import DSPTensionBalancer
from src.narrative_balancer.dsp.models import Beat


def benchmark_dsp(iterations: int = 1000) -> dict:
    beats = [Beat(episode=i, tension=3.0 if 15 <= i <= 25 else 5.0) for i in range(1, 41)]
    balancer = DSPTensionBalancer()

    # Warmup
    for _ in range(50):
        balancer.correct(beats)

    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        balancer.correct(beats)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    p50 = float(np.percentile(latencies, 50))
    p99 = float(np.percentile(latencies, 99))
    return {"p50_ms": p50, "p99_ms": p99}


if __name__ == "__main__":
    res = benchmark_dsp()
    print(f"DSP Benchmark: p50={res['p50_ms']:.3f}ms, p99={res['p99_ms']:.3f}ms")
