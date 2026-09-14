"""Experiment Allocator for A/B Testing.

Phase 2 / Guideline #3: Deterministic traffic allocation for weight variant
A/B testing using consistent hashing.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from src.config.weight_variants import (
    select_variant_for_genre,
    WEIGHT_VARIANTS,
)

logger = logging.getLogger(__name__)


class ExperimentAllocator:
    """Deterministic experiment allocator using consistent hashing.

    Ensures same book_id + genre always gets same variant.
    Supports gradual rollout via traffic_fraction.
    """

    def __init__(
        self,
        traffic_fraction: float = 0.01,  # 1% of traffic in experiment
        seed: str = "autonovel-audit-v1",
    ) -> None:
        """Initialize allocator.

        Args:
            traffic_fraction: Fraction of traffic to include in experiment (0.0-1.0)
            seed: Salt for hash to prevent collision with other experiments
        """
        self.traffic_fraction = max(0.0, min(1.0, traffic_fraction))
        self.seed = seed

    def allocate(self, book_id: int, genre: str = "") -> str:
        """Allocate a weight variant for a book.

        Args:
            book_id: Unique book identifier
            genre: Genre name (used to select genre-appropriate variants)

        Returns:
            Variant name (e.g., "literary_v1", "entertainment_v2_hook_up")
        """
        # Deterministic hash-based bucket assignment
        hash_input = f"{self.seed}:{book_id}:{genre}"
        hash_val = hashlib.md5(hash_input.encode()).hexdigest()
        bucket = int(hash_val, 16) % 10000  # 0-9999

        # Check if in experiment bucket
        experiment_threshold = int(self.traffic_fraction * 10000)

        if bucket >= experiment_threshold:
            # Control group: use genre-appropriate default variant
            return select_variant_for_genre(genre)

        # Experiment group: select from available experimental variants
        return self._select_experimental_variant(genre, bucket)

    def _select_experimental_variant(self, genre: str, bucket: int) -> str:
        """Select experimental variant for genre from bucket."""
        # Get all variants for this genre (excluding base v1)
        genre_base = f"{genre}_v1"
        experimental = [
            name for name in WEIGHT_VARIANTS.keys()
            if name.startswith(f"{genre}_") and name != genre_base
        ]

        if not experimental:
            # No experimental variants for this genre, fall back to base
            return genre_base if genre_base in WEIGHT_VARIANTS else "default_v1"

        # Distribute evenly across experimental variants
        variant_idx = bucket % len(experimental)
        return experimental[variant_idx]

    def get_allocation_info(self, book_id: int, genre: str = "") -> dict[str, Any]:
        """Get detailed allocation info for logging/debugging."""
        hash_input = f"{self.seed}:{book_id}:{genre}"
        hash_val = hashlib.md5(hash_input.encode()).hexdigest()
        bucket = int(hash_val, 16) % 10000
        experiment_threshold = int(self.traffic_fraction * 10000)
        in_experiment = bucket < experiment_threshold

        variant = self.allocate(book_id, genre)

        return {
            "book_id": book_id,
            "genre": genre,
            "hash": hash_val[:16],
            "bucket": bucket,
            "experiment_threshold": experiment_threshold,
            "in_experiment": in_experiment,
            "traffic_fraction": self.traffic_fraction,
            "allocated_variant": variant,
        }


class MultiExperimentAllocator:
    """Manages multiple concurrent experiments with different traffic fractions."""

    def __init__(self) -> None:
        self.experiments: dict[str, ExperimentAllocator] = {}

    def add_experiment(
        self,
        name: str,
        traffic_fraction: float,
        seed: str | None = None,
    ) -> None:
        """Add an experiment.

        Args:
            name: Experiment name
            traffic_fraction: Fraction of traffic for this experiment
            seed: Optional seed (defaults to name)
        """
        self.experiments[name] = ExperimentAllocator(
            traffic_fraction=traffic_fraction,
            seed=seed or name,
        )

    def allocate(self, book_id: int, genre: str = "") -> dict[str, str]:
        """Allocate variants for all experiments.

        Returns:
            Dict mapping experiment_name -> variant_name
        """
        return {
            name: exp.allocate(book_id, genre)
            for name, exp in self.experiments.items()
        }

    def get_default_allocator(self) -> ExperimentAllocator:
        """Get the default experiment allocator (first added)."""
        if not self.experiments:
            return ExperimentAllocator()
        return next(iter(self.experiments.values()))


# Global default allocator (1% traffic)
DEFAULT_ALLOCATOR = ExperimentAllocator(traffic_fraction=0.01)


def allocate_variant(book_id: int, genre: str = "", traffic_fraction: float = 0.01) -> str:
    """Convenience function for simple allocation.

    Args:
        book_id: Book ID
        genre: Genre name
        traffic_fraction: Experiment traffic fraction (default 1%)

    Returns:
        Allocated variant name
    """
    allocator = ExperimentAllocator(traffic_fraction=traffic_fraction)
    return allocator.allocate(book_id, genre)


__all__ = [
    "ExperimentAllocator",
    "MultiExperimentAllocator",
    "DEFAULT_ALLOCATOR",
    "allocate_variant",
]