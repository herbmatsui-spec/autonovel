"""Performance benchmark for CSP Solver Balancer."""

import time
from ortools.sat.python import cp_model
from src.narrative_balancer.csp.balancer import CSPNarrativeBalancer
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.models import Beat, BeatType


def benchmark_csp(iterations: int = 10) -> dict:
    cfg = CSPConfig(n_episodes=20, midpoint_episode=10)
    balancer = CSPNarrativeBalancer(config=cfg)

    beats = [
        Beat(episode=1, tension=4.0, beat_type=BeatType.SETUP),
        Beat(episode=20, tension=9.0, beat_type=BeatType.CLIMAX),
    ]

    # Warmup
    balancer.balance(beats)

    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        balancer.balance(beats)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = sum(latencies) / len(latencies)
    return {"avg_ms": avg_ms, "max_ms": max(latencies)}


if __name__ == "__main__":
    res = benchmark_csp()
    print(f"CSP Benchmark: avg={res['avg_ms']:.2f}ms, max={res['max_ms']:.2f}ms")
