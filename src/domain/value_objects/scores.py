"""Score value objects for quality metrics."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class QualityScore:
    """Individual quality dimension score (0-100)."""
    value: int
    dimension: str

    # Valid dimensions
    VALID_DIMENSIONS: ClassVar[set[str]] = {
        "story", "character", "worldbuilding", "prose", "pacing",
        "dialogue", "tension", "emotion", "originality", "coherence",
        "literary_beauty", "thematic_depth", "erotic_intensity",
        "state_integrity", "emotional_resonance"
    }

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError("Score value must be an integer")
        if not 0 <= self.value <= 100:
            raise ValueError("Score must be between 0 and 100")
        if self.dimension not in self.VALID_DIMENSIONS:
            raise ValueError(f"Invalid dimension: {self.dimension}")

    def is_passing(self, threshold: int = 60) -> bool:
        return self.value >= threshold

    def __str__(self) -> str:
        return f"{self.dimension}: {self.value}/100"


@dataclass(frozen=True, slots=True)
class TensionScore:
    """Tension curve score."""
    value: int  # 0-100
    delta: int = 0  # Change from previous episode

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 100:
            raise ValueError("Tension score must be between 0 and 100")

    def is_catharsis(self) -> bool:
        return self.value >= 80 and self.delta > 20

    def is_rising(self) -> bool:
        return self.delta > 0

    def is_falling(self) -> bool:
        return self.delta < 0


@dataclass(frozen=True, slots=True)
class BookScore:
    """Aggregate book quality score with dimension breakdown."""
    overall: int
    dimensions: dict[str, int] = field(default_factory=dict)

    # Weight for each dimension in overall calculation
    WEIGHTS: ClassVar[dict[str, float]] = {
        "story": 0.20,
        "character": 0.15,
        "worldbuilding": 0.10,
        "prose": 0.15,
        "pacing": 0.10,
        "dialogue": 0.10,
        "tension": 0.10,
        "emotion": 0.10,
    }

    def __post_init__(self) -> None:
        if not 0 <= self.overall <= 100:
            raise ValueError("Overall score must be between 0 and 100")
        for dim, score in self.dimensions.items():
            if not 0 <= score <= 100:
                raise ValueError(f"Dimension {dim} score must be between 0 and 100")

    @classmethod
    def calculate_from_dimensions(cls, dimensions: dict[str, int]) -> BookScore:
        """Calculate overall score from dimension scores using weights."""
        weighted_sum = 0.0
        total_weight = 0.0
        for dim, weight in cls.WEIGHTS.items():
            if dim in dimensions:
                weighted_sum += dimensions[dim] * weight
                total_weight += weight

        overall = int(round(weighted_sum / total_weight)) if total_weight > 0 else 0
        return cls(overall=overall, dimensions=dimensions)

    def get_dimension(self, name: str) -> int | None:
        return self.dimensions.get(name)

    def get_quality_score(self, dimension: str) -> QualityScore | None:
        if dimension in self.dimensions:
            return QualityScore(value=self.dimensions[dimension], dimension=dimension)
        return None

    def __str__(self) -> str:
        dims = ", ".join(f"{k}:{v}" for k, v in self.dimensions.items())
        return f"BookScore(overall={self.overall}, [{dims}])"


@dataclass(frozen=True, slots=True)
class QolScore:
    """Quality of Life score for reader experience."""
    value: int  # 0-100
    factors: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 100:
            raise ValueError("QoL score must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class CostScore:
    """Cost efficiency score."""
    value: float  # USD cost
    tokens_used: int = 0

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Cost cannot be negative")


__all__ = [
    "QualityScore",
    "TensionScore",
    "BookScore",
    "QolScore",
    "CostScore",
]