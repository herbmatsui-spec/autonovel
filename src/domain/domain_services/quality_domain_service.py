"""Quality domain service - pure business logic for quality score calculation and validation."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from src.domain.value_objects.scores import QualityScore, TensionScore, BookScore, QolScore, CostScore
from src.domain.value_objects.ids import NovelId, PlotId


class QualityValidationError(Exception):
    """Raised when quality validation fails."""
    pass


class QualityGrade(Enum):
    """Quality grade based on overall score."""
    S = "S"      # 90-100
    A = "A"      # 80-89
    B = "B"      # 70-79
    C = "C"      # 60-69
    D = "D"      # 50-59
    F = "F"      # 0-49


class QualityThresholds:
    """Quality threshold constants."""
    PASSING_SCORE = 60
    EXCELLENT_SCORE = 80
    MASTERPIECE_SCORE = 90

    CRITICAL_ISSUE_DEDUCTION = 30
    HIGH_ISSUE_DEDUCTION = 15
    MEDIUM_ISSUE_DEDUCTION = 8
    LOW_ISSUE_DEDUCTION = 3
    INFO_ISSUE_DEDUCTION = 1


class QualityValidator:
    """Validates quality scores and dimensions."""

    @staticmethod
    def validate_dimension_score(score: int, dimension: str) -> List[str]:
        """Validate a single dimension score. Returns list of errors."""
        errors = []
        if not 0 <= score <= 100:
            errors.append(f"Dimension '{dimension}' score must be between 0 and 100, got {score}")
        return errors

    @staticmethod
    def validate_book_score(book_score: BookScore) -> List[str]:
        """Validate a BookScore. Returns list of errors."""
        errors = []
        if not 0 <= book_score.overall <= 100:
            errors.append(f"Overall score must be between 0 and 100, got {book_score.overall}")
        for dim, score in book_score.dimensions.items():
            if not 0 <= score <= 100:
                errors.append(f"Dimension '{dim}' score must be between 0 and 100, got {score}")
        return errors

    @staticmethod
    def validate_tension_score(tension: TensionScore) -> List[str]:
        """Validate a TensionScore. Returns list of errors."""
        errors = []
        if not 0 <= tension.value <= 100:
            errors.append(f"Tension value must be between 0 and 100, got {tension.value}")
        return errors

    @staticmethod
    def validate_qol_score(qol: QolScore) -> List[str]:
        """Validate a QolScore. Returns list of errors."""
        errors = []
        if not 0 <= qol.value <= 100:
            errors.append(f"QoL value must be between 0 and 100, got {qol.value}")
        for factor, score in qol.factors.items():
            if not 0 <= score <= 100:
                errors.append(f"QoL factor '{factor}' score must be between 0 and 100, got {score}")
        return errors

    @staticmethod
    def validate_cost_score(cost: CostScore) -> List[str]:
        """Validate a CostScore. Returns list of errors."""
        errors = []
        if cost.value < 0:
            errors.append(f"Cost cannot be negative, got {cost.value}")
        if cost.tokens_used < 0:
            errors.append(f"Tokens used cannot be negative, got {cost.tokens_used}")
        return errors


class QualityCalculator:
    """Calculates aggregate quality scores from dimension scores."""

    # Default weights for BookScore calculation
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "story": 0.20,
        "character": 0.15,
        "worldbuilding": 0.10,
        "prose": 0.15,
        "pacing": 0.10,
        "dialogue": 0.10,
        "tension": 0.10,
        "emotion": 0.10,
    }

    # Quality dimension names that map to Plot entity scores
    PLOT_QUALITY_DIMENSIONS = {
        "state_integrity": "state_integrity_score",
        "emotional_resonance": "emotional_resonance_score",
        "thematic_depth": "thematic_depth_score",
        "literary_beauty": "literary_beauty_score",
        "erotic_intensity": "erotic_intensity",
    }

    @classmethod
    def calculate_book_score(cls, dimensions: Dict[str, int], weights: Optional[Dict[str, float]] = None) -> BookScore:
        """Calculate BookScore from dimension scores using weights."""
        effective_weights = weights or cls.DEFAULT_WEIGHTS
        return BookScore.calculate_from_dimensions(dimensions)

    @classmethod
    def calculate_plot_quality_score(cls, plot) -> BookScore:
        """Calculate quality score for a Plot entity."""
        dimensions = {}
        for dim_name, attr_name in cls.PLOT_QUALITY_DIMENSIONS.items():
            if hasattr(plot, attr_name):
                value = getattr(plot, attr_name)
                if value is not None:
                    dimensions[dim_name] = max(0, min(100, value))
        return cls.calculate_book_score(dimensions)

    @classmethod
    def calculate_chapter_quality_score(cls, chapter) -> Optional[BookScore]:
        """Calculate quality score for a Chapter entity."""
        if chapter.score_story is None:
            return None
        dimensions = {"story": chapter.score_story}
        return cls.calculate_book_score(dimensions)

    @classmethod
    def calculate_aggregate_quality(
        cls,
        plot_scores: List[BookScore],
        chapter_scores: List[Optional[BookScore]],
    ) -> BookScore:
        """Calculate aggregate quality across multiple plots and chapters."""
        all_dimensions: Dict[str, List[int]] = {}

        for score in plot_scores:
            for dim, value in score.dimensions.items():
                all_dimensions.setdefault(dim, []).append(value)

        for score in chapter_scores:
            if score:
                for dim, value in score.dimensions.items():
                    all_dimensions.setdefault(dim, []).append(value)

        averaged = {}
        for dim, values in all_dimensions.items():
            averaged[dim] = int(round(sum(values) / len(values)))

        return cls.calculate_book_score(averaged)

    @classmethod
    def calculate_tension_curve(cls, plots) -> Dict[str, Any]:
        """Analyze tension curve across episodes."""
        if not plots:
            return {"episodes": [], "trend": "unknown", "peaks": [], "valleys": []}

        sorted_plots = sorted(plots, key=lambda p: p.episode_number)
        tensions = [p.tension_score.value for p in sorted_plots]
        episodes = [p.episode_number for p in sorted_plots]

        peaks = []
        valleys = []
        for i in range(1, len(tensions) - 1):
            if tensions[i] > tensions[i - 1] and tensions[i] > tensions[i + 1]:
                peaks.append({"episode": episodes[i], "tension": tensions[i]})
            elif tensions[i] < tensions[i - 1] and tensions[i] < tensions[i + 1]:
                valleys.append({"episode": episodes[i], "tension": tensions[i]})

        trend = "stable"
        if len(tensions) >= 2:
            if tensions[-1] > tensions[0] + 10:
                trend = "rising"
            elif tensions[-1] < tensions[0] - 10:
                trend = "falling"

        return {
            "episodes": list(zip(episodes, tensions)),
            "trend": trend,
            "peaks": peaks,
            "valleys": valleys,
            "average_tension": sum(tensions) / len(tensions),
            "max_tension": max(tensions),
            "min_tension": min(tensions),
        }

    @classmethod
    def calculate_catharsis_distribution(cls, plots) -> Dict[str, Any]:
        """Analyze catharsis distribution across episodes."""
        if not plots:
            return {"total": 0, "distribution": {}, "catharsis_episodes": []}

        catharsis_episodes = []
        distribution = {i: 0 for i in range(0, 101, 10)}

        for plot in plots:
            catharsis = plot.catharsis
            bucket = (catharsis // 10) * 10
            distribution[bucket] = distribution.get(bucket, 0) + 1

            if catharsis >= 80:
                catharsis_episodes.append({
                    "episode": plot.episode_number,
                    "catharsis": catharsis,
                    "type": plot.catharsis_type,
                })

        return {
            "total": len(plots),
            "distribution": distribution,
            "catharsis_episodes": catharsis_episodes,
            "catharsis_rate": len(catharsis_episodes) / len(plots) * 100 if plots else 0,
        }

    @classmethod
    def calculate_cost_efficiency(cls, plots) -> Dict[str, Any]:
        """Calculate cost efficiency metrics."""
        if not plots:
            return {"total_cost": 0.0, "total_tokens": 0, "avg_cost_per_episode": 0.0, "efficiency_score": 100}

        total_cost = sum(getattr(p, "cost_score", 0.0) for p in plots)
        total_tokens = sum(getattr(p, "qol_delta", 0) for p in plots)  # Using qol_delta as proxy

        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "avg_cost_per_episode": total_cost / len(plots) if plots else 0.0,
            "efficiency_score": max(0, 100 - int(total_cost * 10)),  # Simple heuristic
        }

    @classmethod
    def calculate_qol_score(cls, plots) -> QolScore:
        """Calculate Quality of Life score for reader experience."""
        if not plots:
            return QolScore(value=50, factors={})

        factors = {}
        total_qol = 0
        count = 0

        for plot in plots:
            qol_delta = getattr(plot, "qol_delta", 0)
            if qol_delta != 0:
                factors[f"episode_{plot.episode_number}"] = max(0, min(100, 50 + qol_delta))
                total_qol += factors[f"episode_{plot.episode_number}"]
                count += 1

        overall = int(round(total_qol / count)) if count > 0 else 50
        return QolScore(value=overall, factors=factors)

    @classmethod
    def get_quality_grade(cls, score: int) -> QualityGrade:
        """Get quality grade from overall score."""
        if score >= 90:
            return QualityGrade.S
        elif score >= 80:
            return QualityGrade.A
        elif score >= 70:
            return QualityGrade.B
        elif score >= 60:
            return QualityGrade.C
        elif score >= 50:
            return QualityGrade.D
        else:
            return QualityGrade.F

    @classmethod
    def calculate_quality_trend(cls, historical_scores: List[BookScore]) -> Dict[str, Any]:
        """Calculate quality trend over time."""
        if len(historical_scores) < 2:
            return {"trend": "insufficient_data", "change": 0}

        recent = historical_scores[-1].overall
        previous = historical_scores[-2].overall
        change = recent - previous

        if change > 5:
            trend = "improving"
        elif change < -5:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change": change,
            "recent_score": recent,
            "previous_score": previous,
        }


class QualityAnalyzer:
    """Analyzes quality metrics and provides insights."""

    @staticmethod
    def identify_weak_dimensions(book_score: BookScore, threshold: int = 60) -> List[str]:
        """Identify dimensions below threshold."""
        weak = []
        for dim, score in book_score.dimensions.items():
            if score < threshold:
                weak.append(dim)
        return weak

    @staticmethod
    def identify_strong_dimensions(book_score: BookScore, threshold: int = 80) -> List[str]:
        """Identify dimensions above threshold."""
        strong = []
        for dim, score in book_score.dimensions.items():
            if score >= threshold:
                strong.append(dim)
        return strong

    @staticmethod
    def calculate_dimension_balance(book_score: BookScore) -> float:
        """Calculate balance score (0-100) - how evenly distributed are the dimensions."""
        if not book_score.dimensions:
            return 100.0

        scores = list(book_score.dimensions.values())
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        # Lower std_dev = more balanced. Max std_dev when half 0, half 100 = 50
        balance = max(0, 100 - (std_dev / 50) * 100)
        return round(balance, 2)

    @staticmethod
    def generate_quality_report(
        book_score: BookScore,
        plot_scores: List[BookScore],
        chapter_scores: List[Optional[BookScore]],
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        weak_dims = QualityAnalyzer.identify_weak_dimensions(book_score)
        strong_dims = QualityAnalyzer.identify_strong_dimensions(book_score)
        balance = QualityAnalyzer.calculate_dimension_balance(book_score)
        grade = QualityCalculator.get_quality_grade(book_score.overall)

        return {
            "overall_score": book_score.overall,
            "grade": grade.value,
            "dimensions": book_score.dimensions,
            "weak_dimensions": weak_dims,
            "strong_dimensions": strong_dims,
            "balance_score": balance,
            "plot_count": len(plot_scores),
            "chapter_count": len([s for s in chapter_scores if s]),
            "recommendations": QualityAnalyzer._generate_recommendations(weak_dims, balance),
        }

    @staticmethod
    def _generate_recommendations(weak_dims: List[str], balance: float) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if weak_dims:
            recommendations.append(f"Focus on improving: {', '.join(weak_dims)}")

        if balance < 50:
            recommendations.append("Quality dimensions are unbalanced - aim for more even development across all aspects")

        dimension_advice = {
            "story": "Strengthen plot structure and narrative coherence",
            "character": "Deepen character development and arcs",
            "worldbuilding": "Enhance setting detail and internal consistency",
            "prose": "Refine writing style and language craft",
            "pacing": "Adjust scene pacing and chapter rhythm",
            "dialogue": "Improve dialogue naturalness and character voice",
            "tension": "Build and release tension more effectively",
            "emotion": "Deepen emotional resonance and reader connection",
        }

        for dim in weak_dims:
            if dim in dimension_advice:
                recommendations.append(dimension_advice[dim])

        return recommendations


@dataclass
class QualityDomainService:
    """
    Domain service for quality score business logic.

    Pure business logic - no infrastructure dependencies.
    Depends only on domain entities and value objects.
    """

    def __post_init__(self):
        self._validator = QualityValidator()
        self._calculator = QualityCalculator()
        self._analyzer = QualityAnalyzer()

    def calculate_plot_quality(self, plot) -> BookScore:
        """Calculate quality score for a single plot."""
        return self._calculator.calculate_plot_quality_score(plot)

    def calculate_chapter_quality(self, chapter) -> Optional[BookScore]:
        """Calculate quality score for a single chapter."""
        return self._calculator.calculate_chapter_quality_score(chapter)

    def calculate_novel_quality(
        self,
        plots: List,
        chapters: List,
    ) -> BookScore:
        """Calculate aggregate quality score for a novel."""
        plot_scores = [self.calculate_plot_quality(p) for p in plots]
        chapter_scores = [self.calculate_chapter_quality(c) for c in chapters]
        return self._calculator.calculate_aggregate_quality(plot_scores, chapter_scores)

    def validate_plot_scores(self, plot) -> List[str]:
        """Validate all quality scores in a plot."""
        errors = []

        # Validate plot quality dimensions
        for dim_name, attr_name in self._calculator.PLOT_QUALITY_DIMENSIONS.items():
            if hasattr(plot, attr_name):
                value = getattr(plot, attr_name)
                if value is not None:
                    errors.extend(self._validator.validate_dimension_score(value, dim_name))

        # Validate tension score
        errors.extend(self._validator.validate_tension_score(plot.tension_score))

        return errors

    def validate_chapter_scores(self, chapter) -> List[str]:
        """Validate quality scores in a chapter."""
        errors = []

        if chapter.score_story is not None:
            errors.extend(self._validator.validate_dimension_score(chapter.score_story, "story"))

        return errors

    def get_quality_grade(self, overall_score: int) -> QualityGrade:
        """Get quality grade from overall score."""
        return self._calculator.get_quality_grade(overall_score)

    def analyze_tension_curve(self, plots: List) -> Dict[str, Any]:
        """Analyze tension curve across episodes."""
        return self._calculator.calculate_tension_curve(plots)

    def analyze_catharsis_distribution(self, plots: List) -> Dict[str, Any]:
        """Analyze catharsis distribution across episodes."""
        return self._calculator.calculate_catharsis_distribution(plots)

    def analyze_cost_efficiency(self, plots: List) -> Dict[str, Any]:
        """Analyze cost efficiency metrics."""
        return self._calculator.calculate_cost_efficiency(plots)

    def analyze_qol(self, plots: List) -> QolScore:
        """Calculate QoL score for reader experience."""
        return self._calculator.calculate_qol_score(plots)

    def generate_quality_report(
        self,
        novel_id: NovelId,
        plots: List,
        chapters: List,
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report for a novel."""
        book_score = self.calculate_novel_quality(plots, chapters)
        plot_scores = [self.calculate_plot_quality(p) for p in plots]
        chapter_scores = [self.calculate_chapter_quality(c) for c in chapters]

        report = self._analyzer.generate_quality_report(book_score, plot_scores, chapter_scores)
        report["novel_id"] = str(novel_id)
        report["generated_at"] = datetime.now().isoformat()

        # Add detailed analyses
        report["tension_analysis"] = self.analyze_tension_curve(plots)
        report["catharsis_analysis"] = self.analyze_catharsis_distribution(plots)
        report["cost_analysis"] = self.analyze_cost_efficiency(plots)
        report["qol_analysis"] = {
            "value": self.analyze_qol(plots).value,
            "factors": self.analyze_qol(plots).factors,
        }

        return report

    def calculate_quality_trend(self, historical_scores: List[BookScore]) -> Dict[str, Any]:
        """Calculate quality trend over time."""
        return self._calculator.calculate_quality_trend(historical_scores)

    def get_dimension_weights(self) -> Dict[str, float]:
        """Get current dimension weights used in BookScore calculation."""
        return self._calculator.DEFAULT_WEIGHTS.copy()

    def set_custom_weights(self, weights: Dict[str, float]) -> None:
        """Set custom dimension weights (for testing or customization)."""
        # Validate weights sum to ~1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise QualityValidationError(f"Weights must sum to 1.0, got {total}")
        # Note: This modifies class variable, use with caution
        self._calculator.DEFAULT_WEIGHTS = weights


__all__ = [
    "QualityDomainService",
    "QualityValidator",
    "QualityCalculator",
    "QualityAnalyzer",
    "QualityValidationError",
    "QualityGrade",
    "QualityThresholds",
]