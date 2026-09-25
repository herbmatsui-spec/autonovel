"""
Performance benchmark for SubtextEngine (Step 18).
Target: 10,000 blocks in <= 100ms.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock


def run_benchmark(num_blocks: int = 10000) -> float:
    engine = SubtextEngine.create_default()

    sample_templates = [
        ["「私は悲しい」"],
        ["「敵が来た」", "「城門を閉じろ」", "「戦うしかない」"],
        ["「なぜなら君が悪いからだ」"],
        ["「はい」"],
        ["「絶対に殺してやる」"],
        ["風が吹いている。"],
    ]

    blocks = [
        DialogueBlock(
            speaker=f"Speaker_{i % 5}",
            lines=sample_templates[i % len(sample_templates)],
        )
        for i in range(num_blocks)
    ]

    start = time.perf_counter()
    engine.process(blocks)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    print(f"SubtextEngine Benchmark: Processed {num_blocks} blocks in {elapsed_ms:.2f} ms")
    print(f"Throughput: {num_blocks / (elapsed_ms / 1000.0):.0f} blocks/sec")
    return elapsed_ms


if __name__ == "__main__":
    elapsed = run_benchmark(10000)
    if elapsed > 5000.0:
        print(f"WARNING: Benchmark exceeded target: {elapsed:.2f} ms > 5000 ms")
        sys.exit(1)
    else:
        print("PASS: Performance benchmark within acceptable threshold.")
        sys.exit(0)
