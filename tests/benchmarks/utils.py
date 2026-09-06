"""Common utilities for benchmarks."""
from __future__ import annotations

import random
import time
import tracemalloc
from typing import Any, Callable, List
from src.services.compression.layer1_keywords import count_tokens


def measure_memory(func: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Execute function and return (result, peak_memory_mb)."""
    tracemalloc.start()
    result = func(*args, **kwargs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, peak / 1024 / 1024


def measure_time(func: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Execute function and return (result, elapsed_ms)."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    return result, elapsed


def measure_time_and_memory(func: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, float, float]:
    """Execute function and return (result, elapsed_ms, peak_memory_mb)."""
    tracemalloc.start()
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed, peak / 1024 / 1024


def token_count(text: str) -> int:
    """Wrapper for token counting."""
    return count_tokens(text)


def generate_random_string(length: int) -> str:
    """Generate random Japanese-like string for testing."""
    chars = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン"
    return "".join(random.choices(chars, k=length))


def percentile(values: List[float], p: float) -> float:
    """Calculate percentile (0-100)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * p / 100)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def mean(values: List[float]) -> float:
    """Calculate mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


__all__ = [
    "measure_memory",
    "measure_time",
    "measure_time_and_memory",
    "token_count",
    "generate_random_string",
    "percentile",
    "mean",
]