"""Performance benchmark for Grammar Balancer."""

import time
from src.narrative_balancer.grammar.balancer import GrammarNarrativeBalancer
from src.narrative_balancer.models import Beat, BeatType


def benchmark_grammar(iterations: int = 50) -> dict:
    balancer = GrammarNarrativeBalancer()
    beats = [
        Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 41)
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
    res = benchmark_grammar()
    print(f"Grammar Benchmark: avg={res['avg_ms']:.2f}ms, max={res['max_ms']:.2f}ms")
