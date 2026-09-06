"""Multi-episode benchmark engine."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from tests.benchmarks.run_single import benchmark_single_episode, benchmark_episode_data
from tests.benchmarks.fixtures import LongNovelData, EpisodeData
from tests.benchmarks.utils import percentile, mean
from src.services.compression.models import SceneType


def benchmark_episodes(
    episodes: List[Dict[str, Any]],
    book_id: int = 1,
    max_tokens: int = 1500,
    runs_per_ep: int = 2,
) -> List[Dict[str, Any]]:
    """Run benchmark on multiple episodes sequentially."""
    results = []
    for i, ep in enumerate(episodes, 1):
        ep_num = ep.get("ep_num", i)
        scene_type = ep.get("scene_type", "general")
        text = ep["text"]
        entities = ep.get("entities")
        relations = ep.get("relations")

        result = benchmark_single_episode(
            text=text,
            scene_type=scene_type,
            entities=entities,
            relations=relations,
            book_id=book_id,
            ep_num=ep_num,
            max_tokens=max_tokens,
            runs=runs_per_ep,
        )
        results.append(result)

    return results


def benchmark_novel(
    novel: LongNovelData,
    book_id: int = 1,
    max_tokens: int = 1500,
    runs_per_ep: int = 2,
    ep_counts: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Run benchmark on a full novel at specified episode checkpoints."""
    if ep_counts is None:
        ep_counts = [10, 50, 100, 200]
    
    # Filter to requested episode counts
    max_ep = max(ep_counts)
    episodes_to_run = novel.episodes[:max_ep]

    # Convert to dict format
    ep_dicts = [
        {
            "ep_num": ep.ep_num,
            "scene_type": ep.scene_type,
            "text": ep.text,
            "entities": None,
            "relations": None,
        }
        for ep in episodes_to_run
    ]

    # Run all episodes
    all_results = benchmark_episodes(
        ep_dicts, book_id=book_id, max_tokens=max_tokens, runs_per_ep=runs_per_ep
    )

    # Aggregate at checkpoints
    checkpoints = {}
    for cp in ep_counts:
        cp_results = [r for r in all_results if r["ep_num"] <= cp]
        if cp_results:
            checkpoints[cp] = aggregate_results(cp_results)

    return {
        "title": novel.title,
        "total_episodes": novel.total_episodes,
        "checkpoints": checkpoints,
        "all_results": all_results,
    }


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate benchmark results across episodes."""
    if not results:
        return {}

    latencies = [r["latency_ms"]["mean"] for r in results]
    memories = [r["memory_mb"]["mean"] for r in results]
    final_tokens = [r["final_tokens"]["mean"] for r in results]
    reductions = [r["reduction_ratio"]["mean"] for r in results]
    cache_hits = [r["cache_hit_rate"] for r in results]

    def pct_stats(values: List[float]) -> Dict[str, float]:
        return {
            "mean": mean(values),
            "p50": percentile(values, 50),
            "p95": percentile(values, 95),
            "min": min(values),
            "max": max(values),
        }

    # Per scene type breakdown
    scene_types = {}
    for r in results:
        st = r["scene_type"]
        if st not in scene_types:
            scene_types[st] = []
        scene_types[st].append(r)

    scene_breakdown = {}
    for st, st_results in scene_types.items():
        scene_breakdown[st] = {
            "count": len(st_results),
            "latency_ms": pct_stats([r["latency_ms"]["mean"] for r in st_results]),
            "reduction_ratio": pct_stats([r["reduction_ratio"]["mean"] for r in st_results]),
            "final_tokens": pct_stats([r["final_tokens"]["mean"] for r in st_results]),
            "cache_hit_rate": mean([r["cache_hit_rate"] for r in st_results]),
        }

    return {
        "episode_count": len(results),
        "latency_ms": pct_stats(latencies),
        "memory_mb": pct_stats(memories),
        "final_tokens": pct_stats(final_tokens),
        "reduction_ratio": pct_stats(reductions),
        "cache_hit_rate": mean(cache_hits),
        "scene_breakdown": scene_breakdown,
    }


def benchmark_at_episode_counts(
    novel: LongNovelData,
    ep_counts: List[int] = None,
    book_id: int = 1,
    max_tokens: int = 1500,
    runs_per_ep: int = 2,
) -> Dict[str, Any]:
    """Run benchmarks at specific episode counts (independent runs)."""
    if ep_counts is None:
        ep_counts = [10, 50, 100, 200]

    results = {}
    for ep_count in ep_counts:
        if ep_count > novel.total_episodes:
            continue
        # Create fresh generator for each count to ensure independence
        from tests.benchmarks.fixtures import LongNovelGenerator
        gen = LongNovelGenerator(seed=42)
        sub_novel = gen.generate_novel(ep_count)
        results[ep_count] = benchmark_novel(sub_novel, book_id, max_tokens, runs_per_ep)

    return {
        "ep_counts": ep_counts,
        "results": results,
    }


__all__ = [
    "benchmark_episodes",
    "benchmark_novel",
    "aggregate_results",
    "benchmark_at_episode_counts",
]