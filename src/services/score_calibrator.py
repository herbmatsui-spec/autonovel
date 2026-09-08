"""Score Calibration and Normalization Engine (Phase 4 / Part 2).

Normalizes raw scores from 8 specialist auditors across different models,
temperaments, and genres into a standard normal scale (0-100), adjusting for
auditor bias, variance, and self-assessed confidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CalibrationConfig:
    """Configuration for auditor score calibration."""
    target_mean: float = 65.0
    target_std: float = 12.0
    confidence_weight: float = 0.30  # Shrinkage towards prior mean when confidence < 1.0
    outlier_threshold_z: float = 2.5
    clamp_min: float = 10.0
    clamp_max: float = 98.0
    enable_sigmoid_bounds: bool = True


# Prior statistics (empirical mean and standard deviation) for each specialist auditor
DEFAULT_SPECIALIST_PRIORS: dict[str, tuple[float, float]] = {
    "reader_hook": (62.0, 14.0),
    "consistency": (70.0, 10.0),
    "structure": (65.0, 11.0),
    "emotion_curve": (60.0, 13.0),
    "style": (68.0, 10.0),
    "factual": (72.0, 12.0),
    "creativity": (58.0, 15.0),
    "multimodal": (65.0, 12.0),
}

# Genre-specific mean score offsets
GENRE_PRIOR_OFFSETS: dict[str, dict[str, float]] = {
    "fantasy": {"creativity": 3.0, "factual": -2.0, "reader_hook": 2.0},
    "mystery": {"consistency": -3.0, "factual": 3.0, "structure": 2.0},
    "romance": {"emotion_curve": 4.0, "reader_hook": 2.0, "factual": -2.0},
    "scifi": {"factual": 3.0, "consistency": 2.0, "creativity": 2.0},
    "action": {"reader_hook": 4.0, "emotion_curve": 2.0, "structure": 1.0},
    "horror": {"emotion_curve": 3.0, "reader_hook": 3.0, "style": 2.0},
    "general": {},
}


def sigmoid_scale(val: float, center: float = 65.0, scale: float = 15.0) -> float:
    """Sigmoid-based soft clipping to keep scores smoothly within (0, 100)."""
    # map to standard logistic curve scaled to 0-100
    z = (val - center) / scale
    try:
        sig = 1.0 / (1.0 + math.exp(-z))
    except OverflowError:
        sig = 1.0 if z > 0 else 0.0
    return round(10.0 + sig * 88.0, 1)  # Range ~ [10.0, 98.0]


class ScoreCalibrator:
    """Engine for calibrating and standardizing specialist audit scores."""

    def __init__(
        self,
        config: CalibrationConfig | None = None,
        custom_priors: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        self.config = config or CalibrationConfig()
        self.priors = dict(DEFAULT_SPECIALIST_PRIORS)
        if custom_priors:
            self.priors.update(custom_priors)

    def get_prior_stats(self, specialist_name: str, genre: str = "general") -> tuple[float, float]:
        """Retrieve the prior mean and std for a specialist in a specific genre."""
        base_mean, base_std = self.priors.get(specialist_name, (65.0, 12.0))
        offsets = GENRE_PRIOR_OFFSETS.get(genre.lower(), {})
        offset = offsets.get(specialist_name, 0.0)
        return (base_mean + offset, base_std)

    def calibrate_single(
        self,
        specialist_name: str,
        raw_score: float,
        confidence: float = 1.0,
        genre: str = "general",
    ) -> tuple[float, dict[str, Any]]:
        """Calibrate a single raw score.

        Returns:
            (calibrated_score, metadata_dict)
        """
        prior_mean, prior_std = self.get_prior_stats(specialist_name, genre)

        # 1. Z-Score normalization against prior distribution
        std_safe = max(0.1, prior_std)
        z_score = (raw_score - prior_mean) / std_safe

        # 2. Rescale to standardized target distribution
        standardized_score = self.config.target_mean + z_score * self.config.target_std

        # 3. Bayesian shrinkage towards target mean based on confidence
        conf_clamped = max(0.0, min(1.0, confidence))
        effective_weight = 1.0 - (1.0 - conf_clamped) * self.config.confidence_weight
        bayesian_score = effective_weight * standardized_score + (1.0 - effective_weight) * self.config.target_mean

        # 4. Outlier detection
        is_outlier = abs(z_score) >= self.config.outlier_threshold_z

        # 5. Bound clamping
        if self.config.enable_sigmoid_bounds and (bayesian_score < self.config.clamp_min or bayesian_score > self.config.clamp_max):
            final_score = sigmoid_scale(bayesian_score, center=self.config.target_mean, scale=self.config.target_std)
        else:
            final_score = max(self.config.clamp_min, min(self.config.clamp_max, bayesian_score))

        final_score = round(final_score, 1)

        meta = {
            "specialist_name": specialist_name,
            "raw_score": raw_score,
            "prior_mean": round(prior_mean, 1),
            "prior_std": round(prior_std, 1),
            "z_score": round(z_score, 2),
            "confidence": round(conf_clamped, 2),
            "effective_weight": round(effective_weight, 2),
            "standardized_score": round(standardized_score, 1),
            "bayesian_score": round(bayesian_score, 1),
            "is_outlier": is_outlier,
            "calibrated_score": final_score,
            "genre": genre,
        }
        return final_score, meta

    def calibrate_all(
        self,
        scores_by_specialist: dict[str, float | dict[str, Any]],
        genre: str = "general",
    ) -> dict[str, Any]:
        """Calibrate a collection of specialist results or scores.

        Accepts dict of {specialist_name: raw_score} or {specialist_name: {"score": s, "confidence": c}}
        or SpecialistAuditResult-like objects.
        """
        calibrated_scores: dict[str, float] = {}
        metadata_map: dict[str, dict[str, Any]] = {}
        outliers: list[str] = []

        for name, data in scores_by_specialist.items():
            if isinstance(data, (int, float)):
                raw_score = float(data)
                conf = 1.0
            elif isinstance(data, dict):
                raw_score = float(data.get("score", 50.0))
                conf = float(data.get("confidence", 1.0))
            elif hasattr(data, "score"):
                raw_score = float(data.score)
                conf = float(getattr(data, "confidence", 1.0))
            else:
                continue

            cal_score, meta = self.calibrate_single(
                specialist_name=name,
                raw_score=raw_score,
                confidence=conf,
                genre=genre,
            )
            calibrated_scores[name] = cal_score
            metadata_map[name] = meta
            if meta["is_outlier"]:
                outliers.append(name)

        return {
            "calibrated_scores": calibrated_scores,
            "metadata": metadata_map,
            "outliers": outliers,
            "genre": genre,
        }


__all__ = [
    "CalibrationConfig",
    "ScoreCalibrator",
    "DEFAULT_SPECIALIST_PRIORS",
    "GENRE_PRIOR_OFFSETS",
    "sigmoid_scale",
]
