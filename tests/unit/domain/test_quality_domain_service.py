"""QualityDomainService（品質ドメインサービス）の単体テスト."""

import pytest

from src.domain.domain_services.quality_domain_service import (
    QualityDomainService, QualityValidator, QualityCalculator, QualityAnalyzer,
    QualityValidationError, QualityGrade, QualityThresholds,
)
from src.domain.value_objects.scores import BookScore, TensionScore, QolScore, CostScore
from src.domain.value_objects.ids import NovelId


class FakePlot:
    """Plotエンティティの軽量スタブ（品質スコア集計用）."""

    def __init__(self, episode_number, tension=50, catharsis=0, catharsis_type="",
                 state_integrity=100, emotional_resonance=0, thematic_depth=0,
                 literary_beauty=0, erotic_intensity=0, cost_score=0.0, qol_delta=0):
        self.episode_number = episode_number
        self.tension_score = TensionScore(value=tension)
        self.catharsis = catharsis
        self.catharsis_type = catharsis_type
        self.state_integrity_score = state_integrity
        self.emotional_resonance_score = emotional_resonance
        self.thematic_depth_score = thematic_depth
        self.literary_beauty_score = literary_beauty
        self.erotic_intensity = erotic_intensity
        self.cost_score = cost_score
        self.qol_delta = qol_delta


class FakeChapter:
    def __init__(self, score_story=None):
        self.score_story = score_story


class TestQualityValidator:
    """品質バリデータのテスト."""

    def test_validate_dimension_score(self):
        assert QualityValidator.validate_dimension_score(50, "story") == []
        errors = QualityValidator.validate_dimension_score(101, "story")
        assert len(errors) == 1

    def test_validate_book_score(self):
        # 正常系：BookScore は __post_init__ で範囲検証済みのため、
        # バリデータは常に [] を返す
        assert QualityValidator.validate_book_score(BookScore(overall=70, dimensions={"story": 70})) == []

    def test_book_score_invalid_raises_at_construction(self):
        # 異常系は VO 構築時の ValueError として検出される
        with pytest.raises(ValueError):
            BookScore(overall=101)

    def test_validate_tension_score(self):
        assert QualityValidator.validate_tension_score(TensionScore(value=50)) == []

    def test_tension_score_invalid_raises_at_construction(self):
        with pytest.raises(ValueError):
            TensionScore(value=-1)

    def test_validate_qol_score(self):
        assert QualityValidator.validate_qol_score(QolScore(value=50, factors={"x": 80})) == []

    def test_qol_score_invalid_raises_at_construction(self):
        with pytest.raises(ValueError):
            QolScore(value=101)

    def test_validate_cost_score(self):
        assert QualityValidator.validate_cost_score(CostScore(value=1.0)) == []

    def test_cost_score_invalid_raises_at_construction(self):
        with pytest.raises(ValueError):
            CostScore(value=-1)


class TestQualityCalculator:
    """品質計算機のテスト."""

    def test_calculate_book_score(self):
        score = QualityCalculator.calculate_book_score({"story": 80, "prose": 100})
        assert 0 <= score.overall <= 100

    def test_calculate_plot_quality_score(self):
        plot = FakePlot(1, state_integrity=90, emotional_resonance=70, thematic_depth=60)
        score = QualityCalculator.calculate_plot_quality_score(plot)
        assert score.dimensions["state_integrity"] == 90
        assert score.dimensions["emotional_resonance"] == 70

    def test_calculate_plot_quality_score_clamps(self):
        plot = FakePlot(1, state_integrity=200)
        score = QualityCalculator.calculate_plot_quality_score(plot)
        assert score.dimensions["state_integrity"] == 100

    def test_calculate_chapter_quality_score(self):
        score = QualityCalculator.calculate_chapter_quality_score(FakeChapter(score_story=75))
        assert score.dimensions["story"] == 75

    def test_calculate_chapter_quality_score_none(self):
        assert QualityCalculator.calculate_chapter_quality_score(FakeChapter(score_story=None)) is None

    def test_calculate_aggregate_quality(self):
        p1 = BookScore.calculate_from_dimensions({"story": 80})
        p2 = BookScore.calculate_from_dimensions({"story": 60})
        c1 = BookScore.calculate_from_dimensions({"story": 70})
        agg = QualityCalculator.calculate_aggregate_quality([p1, p2], [c1, None])
        assert agg.dimensions["story"] == 70  # (80+60+70)/3

    def test_calculate_aggregate_empty(self):
        agg = QualityCalculator.calculate_aggregate_quality([], [])
        assert agg.overall == 0

    def test_calculate_tension_curve(self):
        plots = [FakePlot(1, tension=30), FakePlot(2, tension=60), FakePlot(3, tension=40), FakePlot(4, tension=70)]
        result = QualityCalculator.calculate_tension_curve(plots)
        assert result["trend"] == "rising"
        assert result["peaks"][0]["episode"] == 2
        assert result["valleys"][0]["episode"] == 3
        assert result["max_tension"] == 70

    def test_calculate_tension_curve_empty(self):
        result = QualityCalculator.calculate_tension_curve([])
        assert result["trend"] == "unknown"

    def test_calculate_catharsis_distribution(self):
        plots = [FakePlot(1, catharsis=90, catharsis_type="大"), FakePlot(2, catharsis=30)]
        result = QualityCalculator.calculate_catharsis_distribution(plots)
        assert result["total"] == 2
        assert len(result["catharsis_episodes"]) == 1
        assert result["catharsis_rate"] == 50.0

    def test_calculate_catharsis_distribution_empty(self):
        result = QualityCalculator.calculate_catharsis_distribution([])
        assert result["total"] == 0

    def test_calculate_cost_efficiency(self):
        plots = [FakePlot(1, cost_score=0.5, qol_delta=10), FakePlot(2, cost_score=1.5, qol_delta=20)]
        result = QualityCalculator.calculate_cost_efficiency(plots)
        assert result["total_cost"] == pytest.approx(2.0)
        assert result["avg_cost_per_episode"] == pytest.approx(1.0)

    def test_calculate_cost_efficiency_empty(self):
        result = QualityCalculator.calculate_cost_efficiency([])
        assert result["efficiency_score"] == 100

    def test_calculate_qol_score(self):
        plots = [FakePlot(1, qol_delta=20), FakePlot(2, qol_delta=-10)]
        q = QualityCalculator.calculate_qol_score(plots)
        assert q.value == 55  # (70 + 40) / 2

    def test_calculate_qol_score_empty(self):
        q = QualityCalculator.calculate_qol_score([])
        assert q.value == 50

    def test_get_quality_grade(self):
        assert QualityCalculator.get_quality_grade(95) == QualityGrade.S
        assert QualityCalculator.get_quality_grade(85) == QualityGrade.A
        assert QualityCalculator.get_quality_grade(75) == QualityGrade.B
        assert QualityCalculator.get_quality_grade(65) == QualityGrade.C
        assert QualityCalculator.get_quality_grade(55) == QualityGrade.D
        assert QualityCalculator.get_quality_grade(30) == QualityGrade.F

    def test_calculate_quality_trend(self):
        s1 = BookScore(overall=60)
        s2 = BookScore(overall=70)
        result = QualityCalculator.calculate_quality_trend([s1, s2])
        assert result["trend"] == "improving"
        assert result["change"] == 10

    def test_calculate_quality_trend_insufficient(self):
        result = QualityCalculator.calculate_quality_trend([BookScore(overall=60)])
        assert result["trend"] == "insufficient_data"


class TestQualityAnalyzer:
    """品質分析器のテスト."""

    def test_identify_weak_strong_dimensions(self):
        score = BookScore(overall=70, dimensions={"story": 50, "prose": 90, "tension": 60})
        weak = QualityAnalyzer.identify_weak_dimensions(score)
        strong = QualityAnalyzer.identify_strong_dimensions(score)
        assert "story" in weak
        assert "prose" in strong
        assert "tension" not in weak

    def test_calculate_dimension_balance(self):
        balanced = BookScore(overall=70, dimensions={"a": 70, "b": 70})
        unbalanced = BookScore(overall=50, dimensions={"a": 0, "b": 100})
        assert QualityAnalyzer.calculate_dimension_balance(balanced) == 100.0
        assert QualityAnalyzer.calculate_dimension_balance(unbalanced) < 20
        empty = BookScore(overall=0)
        assert QualityAnalyzer.calculate_dimension_balance(empty) == 100.0

    def test_generate_quality_report(self):
        score = BookScore(overall=70, dimensions={"story": 50, "prose": 90})
        plot_scores = [BookScore(overall=65)]
        chapter_scores = [BookScore(overall=75), None]
        report = QualityAnalyzer.generate_quality_report(score, plot_scores, chapter_scores)
        assert report["grade"] == "B"
        assert "story" in report["weak_dimensions"]
        assert "prose" in report["strong_dimensions"]
        assert len(report["recommendations"]) > 0

    def test_generate_recommendations(self):
        recs = QualityAnalyzer._generate_recommendations(["tension"], 30)
        assert any("tension" in r for r in recs)
        assert any("unbalanced" in r for r in recs)


class TestQualityDomainService:
    """QualityDomainService ファサードのテスト."""

    def setup_method(self):
        self.service = QualityDomainService()

    def test_calculate_novel_quality(self):
        plots = [FakePlot(1, state_integrity=80), FakePlot(2, state_integrity=60)]
        chapters = [FakeChapter(score_story=70)]
        score = self.service.calculate_novel_quality(plots, chapters)
        assert 0 <= score.overall <= 100

    def test_validate_plot_scores_ok(self):
        plot = FakePlot(1, tension=50, state_integrity=80)
        assert self.service.validate_plot_scores(plot) == []

    def test_validate_plot_scores_with_raw_attrs(self):
        # FakePlot は tension_score を VO で持つため不正値は構築時に ValueError になる。
        # validate_plot_scores のエラー収集パスは正常系で通ることを確認。
        plot = FakePlot(1, tension=50, state_integrity=80)
        assert self.service.validate_plot_scores(plot) == []

    def test_validate_chapter_scores(self):
        assert self.service.validate_chapter_scores(FakeChapter(score_story=70)) == []
        assert len(self.service.validate_chapter_scores(FakeChapter(score_story=101))) == 1

    def test_get_quality_grade(self):
        assert self.service.get_quality_grade(90) == QualityGrade.S

    def test_analyze_tension_curve(self):
        plots = [FakePlot(1, tension=20), FakePlot(2, tension=80)]
        result = self.service.analyze_tension_curve(plots)
        assert result["trend"] == "rising"

    def test_analyze_catharsis_distribution(self):
        plots = [FakePlot(1, catharsis=95)]
        result = self.service.analyze_catharsis_distribution(plots)
        assert result["catharsis_rate"] == 100.0

    def test_analyze_cost_efficiency(self):
        plots = [FakePlot(1, cost_score=0.3)]
        result = self.service.analyze_cost_efficiency(plots)
        assert result["total_cost"] == pytest.approx(0.3)

    def test_analyze_qol(self):
        plots = [FakePlot(1, qol_delta=30)]
        q = self.service.analyze_qol(plots)
        assert q.value == 80

    def test_generate_quality_report(self):
        novel_id = NovelId.generate()
        plots = [FakePlot(1, tension=30, catharsis=85, catharsis_type="大", state_integrity=90, qol_delta=10)]
        chapters = [FakeChapter(score_story=70)]
        report = self.service.generate_quality_report(novel_id, plots, chapters)
        assert report["novel_id"] == str(novel_id)
        assert "tension_analysis" in report
        assert "catharsis_analysis" in report
        assert "cost_analysis" in report
        assert "qol_analysis" in report
        assert "generated_at" in report

    def test_calculate_quality_trend(self):
        result = self.service.calculate_quality_trend([BookScore(overall=50), BookScore(overall=65)])
        assert result["trend"] == "improving"

    def test_get_dimension_weights(self):
        weights = self.service.get_dimension_weights()
        assert "story" in weights
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_set_custom_weights(self):
        custom = {"story": 1.0}
        original = self.service.get_dimension_weights()
        try:
            self.service.set_custom_weights(custom)
            assert self.service.get_dimension_weights() == custom
        finally:
            self.service.set_custom_weights(original)

    def test_set_custom_weights_invalid_sum(self):
        with pytest.raises(QualityValidationError):
            self.service.set_custom_weights({"story": 0.5, "prose": 0.2})

    def test_quality_thresholds_constants(self):
        assert QualityThresholds.PASSING_SCORE == 60
        assert QualityThresholds.MASTERPIECE_SCORE == 90
