"""Unified BookScore Mapping Engine (Phase 4 / Part 3).

Mathematically maps calibrated scores from 8 specialist auditors into the
5 standard BookScore dimensions:
1. structure_score (構成力)
2. coherency_score (論理一貫性)
3. factual_grounding_score (事実性・設定根拠)
4. visual_textual_synergy_score (視覚・情景調和)
5. reader_experience_score (読者体験・感情・牽引力)

Supports genre-specific matrix adjustments, phase-based dynamic shifting,
and mathematical proportional re-normalization when specialists are missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# 5 Core BookScore Dimensions
BOOK_SCORE_DIMENSIONS: tuple[str, ...] = (
    "structure_score",
    "coherency_score",
    "factual_grounding_score",
    "visual_textual_synergy_score",
    "reader_experience_score",
)

# Base Transformation Matrix (Dimension -> Specialist -> Weight)
# Weights per dimension must sum to 1.0
BASE_TRANSFORMATION_MATRIX: dict[str, dict[str, float]] = {
    "structure_score": {
        "structure": 0.70,
        "reader_hook": 0.15,
        "consistency": 0.15,
    },
    "coherency_score": {
        "consistency": 0.65,
        "style": 0.20,
        "structure": 0.15,
    },
    "factual_grounding_score": {
        "factual": 0.75,
        "consistency": 0.25,
    },
    "visual_textual_synergy_score": {
        "multimodal": 0.60,
        "style": 0.25,
        "creativity": 0.15,
    },
    "reader_experience_score": {
        "reader_hook": 0.35,
        "emotion_curve": 0.35,
        "creativity": 0.15,
        "style": 0.15,
    },
}

# Genre-specific overrides to the transformation matrix
GENRE_MATRIX_OVERRIDES: dict[str, dict[str, dict[str, float]]] = {
    "mystery": {
        "coherency_score": {
            "consistency": 0.75,
            "structure": 0.15,
            "factual": 0.10,
        },
        "reader_experience_score": {
            "reader_hook": 0.45,
            "emotion_curve": 0.30,
            "creativity": 0.15,
            "style": 0.10,
        },
    },
    "romance": {
        "reader_experience_score": {
            "emotion_curve": 0.50,
            "reader_hook": 0.25,
            "style": 0.15,
            "creativity": 0.10,
        },
        "visual_textual_synergy_score": {
            "multimodal": 0.45,
            "style": 0.35,
            "creativity": 0.20,
        },
    },
    "action": {
        "structure_score": {
            "structure": 0.60,
            "reader_hook": 0.25,
            "consistency": 0.15,
        },
        "reader_experience_score": {
            "reader_hook": 0.40,
            "emotion_curve": 0.40,
            "creativity": 0.10,
            "style": 0.10,
        },
    },
    "fantasy": {
        "visual_textual_synergy_score": {
            "multimodal": 0.50,
            "creativity": 0.30,
            "style": 0.20,
        },
        "factual_grounding_score": {
            "factual": 0.60,
            "consistency": 0.40,  # World Bible rule adherence is vital in fantasy
        },
    },
}

# Dimension weights in overall score (Default: 20% each = equal weight)
DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "structure_score": 0.20,
    "coherency_score": 0.20,
    "factual_grounding_score": 0.20,
    "visual_textual_synergy_score": 0.20,
    "reader_experience_score": 0.20,
}

# Phase-based dynamic shifts in dimension weights
PHASE_DIMENSION_SHIFTS: dict[str, dict[str, float]] = {
    "plot": {
        "structure_score": 0.35,
        "coherency_score": 0.30,
        "factual_grounding_score": 0.15,
        "visual_textual_synergy_score": 0.05,
        "reader_experience_score": 0.15,
    },
    "draft": {
        "structure_score": 0.15,
        "coherency_score": 0.15,
        "factual_grounding_score": 0.15,
        "visual_textual_synergy_score": 0.25,
        "reader_experience_score": 0.30,
    },
    "revision": {
        "structure_score": 0.20,
        "coherency_score": 0.30,
        "factual_grounding_score": 0.20,
        "visual_textual_synergy_score": 0.10,
        "reader_experience_score": 0.20,
    },
}


@dataclass
class Unified5DScore:
    """Represents the 5-dimensional unified BookScore with detailed contributions."""
    overall_score: float
    structure_score: float
    coherency_score: float
    factual_grounding_score: float
    visual_textual_synergy_score: float
    reader_experience_score: float
    dimension_weights: dict[str, float] = field(default_factory=dict)
    contributions: dict[str, dict[str, float]] = field(default_factory=dict)  # dim -> spec -> points
    missing_specialists: list[str] = field(default_factory=list)
    genre: str = "general"
    phase: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "structure_score": round(self.structure_score, 2),
            "coherency_score": round(self.coherency_score, 2),
            "factual_grounding_score": round(self.factual_grounding_score, 2),
            "visual_textual_synergy_score": round(self.visual_textual_synergy_score, 2),
            "reader_experience_score": round(self.reader_experience_score, 2),
            "dimension_weights": {k: round(v, 4) for k, v in self.dimension_weights.items()},
            "contributions": {
                dim: {k: round(v, 2) for k, v in specs.items()}
                for dim, specs in self.contributions.items()
            },
            "missing_specialists": list(self.missing_specialists),
            "genre": self.genre,
            "phase": self.phase,
        }

    def lowest_dimension(self) -> str:
        """Return the lowest scoring 5D dimension name."""
        dims = {
            "structure_score": self.structure_score,
            "coherency_score": self.coherency_score,
            "factual_grounding_score": self.factual_grounding_score,
            "visual_textual_synergy_score": self.visual_textual_synergy_score,
            "reader_experience_score": self.reader_experience_score,
        }
        return min(dims, key=dims.get)


class UnifiedBookScoreBridge:
    """Bridges 8 specialist auditor scores into 5D BookScore with genre and phase tuning."""

    def __init__(
        self,
        base_matrix: dict[str, dict[str, float]] | None = None,
        dimension_weights: dict[str, float] | None = None,
    ) -> None:
        self.base_matrix = dict(base_matrix or BASE_TRANSFORMATION_MATRIX)
        self.dimension_weights = dict(dimension_weights or DEFAULT_DIMENSION_WEIGHTS)

    def get_matrix_for_genre(self, genre: str = "general") -> dict[str, dict[str, float]]:
        """Get transformation matrix customized for a specific genre."""
        matrix = {dim: dict(specs) for dim, specs in self.base_matrix.items()}
        g = genre.lower().strip()
        if g in GENRE_MATRIX_OVERRIDES:
            for dim, overrides in GENRE_MATRIX_OVERRIDES[g].items():
                if dim in matrix:
                    matrix[dim] = dict(overrides)
        return matrix

    def get_dimension_weights_for_phase(self, phase: str = "draft") -> dict[str, float]:
        """Get dimension weights customized for production phase (plot/draft/revision)."""
        p = phase.lower().strip()
        if p in PHASE_DIMENSION_SHIFTS:
            return dict(PHASE_DIMENSION_SHIFTS[p])
        return dict(self.dimension_weights)

    def map_to_5d(
        self,
        specialist_scores: Mapping[str, float],
        genre: str = "general",
        phase: str = "draft",
    ) -> Unified5DScore:
        """Map specialist scores to the 5 BookScore dimensions.

        Handles missing specialists via proportional re-normalization.
        """
        matrix = self.get_matrix_for_genre(genre)
        dim_weights = self.get_dimension_weights_for_phase(phase)

        scores_5d: dict[str, float] = {}
        contributions: dict[str, dict[str, float]] = {}
        missing_specs: set[str] = set()

        for dim, spec_weights in matrix.items():
            # Filter present specialists for this dimension
            present_specs = {
                s: w for s, w in spec_weights.items() if s in specialist_scores
            }
            missing = [s for s in spec_weights if s not in specialist_scores]
            missing_specs.update(missing)

            if not present_specs:
                # Default neutral score if completely absent
                scores_5d[dim] = 50.0
                contributions[dim] = {}
                continue

            # Step 29: Proportional re-normalization of weights
            total_weight = sum(present_specs.values())
            if total_weight > 0:
                normalized_weights = {s: w / total_weight for s, w in present_specs.items()}
            else:
                eq = 1.0 / len(present_specs)
                normalized_weights = {s: eq for s in present_specs}

            dim_score = 0.0
            dim_contrib: dict[str, float] = {}
            for s, w in normalized_weights.items():
                pts = specialist_scores[s] * w
                dim_score += pts
                dim_contrib[s] = pts

            scores_5d[dim] = round(dim_score, 2)
            contributions[dim] = dim_contrib

        # Overall score: weighted sum across 5 dimensions
        overall = sum(scores_5d[dim] * dim_weights.get(dim, 0.20) for dim in BOOK_SCORE_DIMENSIONS)
        overall = round(max(0.0, min(100.0, overall)), 2)

        return Unified5DScore(
            overall_score=overall,
            structure_score=scores_5d.get("structure_score", 50.0),
            coherency_score=scores_5d.get("coherency_score", 50.0),
            factual_grounding_score=scores_5d.get("factual_grounding_score", 50.0),
            visual_textual_synergy_score=scores_5d.get("visual_textual_synergy_score", 50.0),
            reader_experience_score=scores_5d.get("reader_experience_score", 50.0),
            dimension_weights=dim_weights,
            contributions=contributions,
            missing_specialists=sorted(list(missing_specs)),
            genre=genre,
            phase=phase,
        )


__all__ = [
    "UnifiedBookScoreBridge",
    "Unified5DScore",
    "BOOK_SCORE_DIMENSIONS",
    "BASE_TRANSFORMATION_MATRIX",
    "GENRE_MATRIX_OVERRIDES",
    "DEFAULT_DIMENSION_WEIGHTS",
    "PHASE_DIMENSION_SHIFTS",
]
