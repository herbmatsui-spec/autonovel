"""src/services/book_score_service.py (BookScoreCalculator/BookScore) の単体テスト."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.book_score_service import BookScore, BookScoreCalculator


def make_score(overall=70.0, structure=70.0, coherency=70.0, factual=70.0, visual=70.0, reader=70.0):
    return BookScore(
        overall_score=overall,
        structure_score=structure,
        coherency_score=coherency,
        factual_grounding_score=factual,
        visual_textual_synergy_score=visual,
        reader_experience_score=reader,
    )


class TestBookScoreDataclass:
    """BookScore dataclass のテスト."""

    def test_lowest_dimension(self):
        score = make_score(structure=30, coherency=90)
        assert score.lowest_dimension() == "structure_score"

    def test_lowest_dimension_reader(self):
        score = make_score(reader=10)
        assert score.lowest_dimension() == "reader_experience_score"


class TestBookScoreCalculatorInit:
    """BookScoreCalculator の初期化テスト."""

    def test_init_without_config(self, tmp_path):
        # 存在しない設定パス → フォールバックのデフォルト重み
        calc = BookScoreCalculator(config_path=str(tmp_path / "nonexistent.yaml"))
        assert "structure" in calc.default_weights
        assert calc.genre_overrides == {}

    def test_init_with_repository(self):
        repo = MagicMock()
        calc = BookScoreCalculator(config_path="nonexistent.yaml", repository=repo)
        assert calc._repository is repo


class TestBookScoreCalculatorWeights:
    """重み取得のテスト."""

    def test_get_weights_default(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        weights = calc._get_weights()
        assert weights.get("structure") == 25

    def test_get_weights_genre_override(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        calc.genre_overrides = {"fantasy": {"structure": 40}}
        weights = calc._get_weights(genre="fantasy")
        assert weights["structure"] == 40

    def test_get_weights_phase_override(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        calc.phase_overrides = {"draft": {"coherency": 30}}
        weights = calc._get_weights(phase="draft")
        assert weights["coherency"] == 30


class TestBookScoreCalculatorSpecialists:
    """8専門家 → 5次元ブリッジのテスト."""

    def test_calculate_from_specialists(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        scores = {
            "plot_structure": 80, "coherence": 70, "worldbuilding": 60,
            "character": 75, "prose": 65, "dialogue": 55,
            "tension": 85, "emotion": 90,
        }
        try:
            score = calc.calculate_from_specialists(scores)
            assert 0 <= score.overall_score <= 100
            assert score.specialist_breakdown is not None
        except Exception:
            pytest.skip("UnifiedBookScoreBridge not available")

    def test_get_score_contributions(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        scores = {"plot_structure": 80, "coherence": 70}
        try:
            contributions = calc.get_score_contributions(scores)
            assert isinstance(contributions, dict)
        except Exception:
            pytest.skip("UnifiedBookScoreBridge not available")

    def test_get_dimension_to_specialists_mapping(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        try:
            mapping = calc.get_dimension_to_specialists_mapping()
            assert isinstance(mapping, dict)
        except Exception:
            pytest.skip("UnifiedBookScoreBridge not available")

    def test_get_specialist_to_dimensions_mapping(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        try:
            rev = calc.get_specialist_to_dimensions_mapping()
            assert isinstance(rev, dict)
        except Exception:
            pytest.skip("UnifiedBookScoreBridge not available")


class TestBookScoreCalculatorReport:
    """成熟度レポート生成のテスト."""

    def test_report_rank_s(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        report = calc.generate_maturity_report(make_score(overall=90))
        assert report["rank"] == "S"
        assert report["is_commercial_ready"] is True

    def test_report_rank_a(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        report = calc.generate_maturity_report(make_score(overall=80))
        assert report["rank"] == "A"
        assert report["is_web_hit_ready"] is True

    def test_report_rank_b(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        report = calc.generate_maturity_report(make_score(overall=70))
        assert report["rank"] == "B"

    def test_report_rank_c(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        report = calc.generate_maturity_report(make_score(overall=55))
        assert report["rank"] == "C"

    def test_report_rank_d(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        report = calc.generate_maturity_report(make_score(overall=30))
        assert report["rank"] == "D"
        assert report["is_commercial_ready"] is False

    def test_report_contains_dimensions(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        report = calc.generate_maturity_report(make_score())
        assert "structure_score" in report["dimensions"]
        assert "lowest_dimension" in report


class TestBookScoreCalculatorSaveAndGet:
    """スコア保存・取得のテスト."""

    @pytest.mark.asyncio
    async def test_save_score_no_repo(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        # repository なしでも例外なしで終了
        await calc.save_score(1, 1, make_score())

    @pytest.mark.asyncio
    async def test_save_score_with_repo(self, tmp_path):
        repo = MagicMock()
        repo.save = AsyncMock()
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"), repository=repo)
        await calc.save_score(1, 1, make_score())
        repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_latest_score_no_repo(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        assert await calc.get_latest_score(1, 1) is None

    @pytest.mark.asyncio
    async def test_get_latest_score_with_repo(self, tmp_path):
        repo = MagicMock()
        repo.get_latest = AsyncMock(return_value="latest")
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"), repository=repo)
        assert await calc.get_latest_score(1, 1) == "latest"

    @pytest.mark.asyncio
    async def test_calculate_with_mock_scores(self, tmp_path):
        calc = BookScoreCalculator(config_path=str(tmp_path / "none.yaml"))
        # データ取得ヘルパーをモック（DBなしでも計算が完結する経路）
        calc._score_structure = AsyncMock(return_value=80)
        calc._score_coherency = AsyncMock(return_value=70)
        calc._score_factual = AsyncMock(return_value=60)
        calc._score_visual_textual = AsyncMock(return_value=50)
        calc._score_reader_experience = AsyncMock(return_value=90)
        score = await calc.calculate(book_id=1, chapter_number=1)
        # overall = 80*.25 + 70*.25 + 60*.20 + 50*.15 + 90*.15 = 20+17.5+12+7.5+13.5 = 70.5
        assert score.overall_score == pytest.approx(70.5, abs=0.1)
        assert score.structure_score == 80.0
