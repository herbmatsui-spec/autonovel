"""Single episode benchmark engine."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from tests.benchmarks.utils import measure_time_and_memory, token_count
from tests.benchmarks.compressor_wrapper import CompressorWrapper
from tests.benchmarks.fixtures import EpisodeData
from src.services.compression.models import SceneType


def benchmark_single_episode(
    text: str,
    scene_type: SceneType = "general",
    entities: Optional[List[Dict[str, Any]]] = None,
    relations: Optional[List[Dict[str, Any]]] = None,
    book_id: int = 1,
    ep_num: int = 1,
    max_tokens: int = 1500,
    runs: int = 3,
) -> Dict[str, Any]:
    """Run compression benchmark on a single episode multiple times."""
    wrapper = CompressorWrapper()

    latencies = []
    memories = []
    tokens = []
    reductions = []
    final_texts = []

    for run in range(runs):
        # Use bypass_cache=True for first run, then False to test cache
        bypass = (run == 0)
        result, elapsed_ms, peak_mb = measure_time_and_memory(
            wrapper.compress_episode,
            text=text,
            scene_type=scene_type,
            entities=entities,
            relations=relations,
            book_id=book_id,
            ep_num=ep_num,
            bypass_cache=bypass,
        )

        latencies.append(elapsed_ms)
        memories.append(peak_mb)
        tokens.append(result["final_tokens"])
        reductions.append(result["reduction_ratio"])
        final_texts.append(result["final_text"])

    # Calculate statistics
    def stats(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"mean": 0, "p50": 0, "p95": 0, "min": 0, "max": 0}
        sorted_v = sorted(values)
        n = len(sorted_v)
        return {
            "mean": sum(values) / n,
            "p50": sorted_v[n // 2],
            "p95": sorted_v[min(int(n * 0.95), n - 1)],
            "min": sorted_v[0],
            "max": sorted_v[-1],
        }

    return {
        "ep_num": ep_num,
        "scene_type": scene_type,
        "original_tokens": token_count(text),
        "runs": runs,
        "latency_ms": stats(latencies),
        "memory_mb": stats(memories),
        "final_tokens": stats(tokens),
        "reduction_ratio": stats(reductions),
        "cache_hit_rate": sum(1 for r in range(1, runs) if wrapper.compress_episode(
            text=text, scene_type=scene_type, entities=entities, relations=relations,
            book_id=book_id, ep_num=ep_num, bypass_cache=False
        )["from_cache"]) / max(1, runs - 1) if runs > 1 else 0.0,
        "sample_output": final_texts[0][:200] if final_texts else "",
    }


def benchmark_episode_data(
    episode: EpisodeData,
    book_id: int = 1,
    max_tokens: int = 1500,
    runs: int = 3,
) -> Dict[str, Any]:
    """Benchmark using EpisodeData fixture."""
    return benchmark_single_episode(
        text=episode.text,
        scene_type=episode.scene_type,
        book_id=book_id,
        ep_num=episode.ep_num,
        max_tokens=max_tokens,
        runs=runs,
    )


__all__ = ["benchmark_single_episode", "benchmark_episode_data"]