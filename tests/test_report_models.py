"""tests/test_report_models.py - レポートモデルのテスト"""
import pytest
from datetime import datetime

from src.models.report import (
    TokenUsageReport,
    QualityMetricsReport,
    EpisodeSummary,
    ProductionReport
)


class TestTokenUsageReport:
    """TokenUsageReport のテスト"""

    def test_create_default(self):
        """デフォルト値で作成"""
        report = TokenUsageReport()
        assert report.total_tokens == 0
        assert report.input_tokens == 0
        assert report.output_tokens == 0
        assert report.episode_count == 0
        assert report.generation_time_seconds == 0.0

    def test_add_usage(self):
        """使用量加算のテスト"""
        report = TokenUsageReport()
        report.add_usage(100, 200)
        assert report.input_tokens == 100
        assert report.output_tokens == 200
        assert report.total_tokens == 300

    def test_add_multiple_usage(self):
        """複数回の使用料加算テスト"""
        report = TokenUsageReport()
        report.add_usage(100, 200)
        report.add_usage(150, 250)
        assert report.input_tokens == 250
        assert report.output_tokens == 450
        assert report.total_tokens == 700


class TestQualityMetricsReport:
    """QualityMetricsReport のテスト"""

    def test_create_default(self):
        """デフォルト値で作成"""
        report = QualityMetricsReport()
        assert report.coherence_score == 0.0
        assert report.character_consistency == 0.0

    def test_create_with_values(self):
        """値指定で作成"""
        report = QualityMetricsReport(
            coherence_score=0.85,
            character_consistency=0.90,
            pacing_score=0.78,
            hook_retention=0.82,
            emotional_resonance=0.75,
            commercial_viability=0.88
        )
        assert report.coherence_score == 0.85
        assert report.character_consistency == 0.90
        assert report.pacing_score == 0.78


class TestEpisodeSummary:
    """EpisodeSummary のテスト"""

    def test_create(self):
        """作成テスト"""
        summary = EpisodeSummary(
            ep_num=1,
            title="第1話 始まり",
            word_count=3000,
            summary="物語の幕開け。",
            quality_score=0.85
        )
        assert summary.ep_num == 1
        assert summary.title == "第1話 始まり"
        assert summary.word_count == 3000


class TestProductionReport:
    """ProductionReport のテスト"""

    def test_create_minimal(self):
        """最小構成で作成"""
        report = ProductionReport(
            title="テスト作品",
            genre="fantasy"
        )
        assert report.title == "テスト作品"
        assert report.genre == "fantasy"
        assert report.target_word_count == 3000
        assert report.episode_summaries == []

    def test_create_full(self):
        """完全構成で作成"""
        token_usage = TokenUsageReport(
            total_tokens=150000,
            input_tokens=80000,
            output_tokens=70000,
            episode_count=10,
            generation_time_seconds=300.0
        )
        quality_metrics = QualityMetricsReport(
            coherence_score=0.85,
            character_consistency=0.90,
            pacing_score=0.78,
            hook_retention=0.82,
            emotional_resonance=0.75,
            commercial_viability=0.88
        )
        episodes = [
            EpisodeSummary(
                ep_num=i,
                title=f"第{i}話",
                word_count=3000,
                summary=f"第{i}話の要約",
                quality_score=0.8
            )
            for i in range(1, 11)
        ]
        report = ProductionReport(
            title="覇者の帰還",
            genre="fantasy",
            target_word_count=3000,
            token_usage=token_usage,
            quality_metrics=quality_metrics,
            episode_summaries=episodes,
            total_generation_time=300.0,
            created_at=datetime.now()
        )
        assert report.title == "覇者の帰還"
        assert report.token_usage.total_tokens == 150000
        assert len(report.episode_summaries) == 10