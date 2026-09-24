"""Unit tests for WritingCoordinator."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.domain.writing.coordinator import WritingCoordinator
from src.domain.writing.models import WritingGenerationContext


class TestWritingCoordinator:
    """Tests for WritingCoordinator."""

    @pytest.fixture
    def mock_writer(self):
        writer = AsyncMock()
        writer.generate_episodes_pipeline = AsyncMock(return_value=(1000, []))
        writer.generate_episodes = AsyncMock(return_value=1000)
        writer.analyze_and_import_chapter = AsyncMock(return_value="imported")
        return writer

    @pytest.fixture
    def mock_book_score_calculator(self):
        calculator = AsyncMock()
        score_obj = MagicMock()
        score_obj.overall_score = 80.0
        score_obj.structure_score = 80.0
        score_obj.coherency_score = 80.0
        score_obj.factual_grounding_score = 80.0
        score_obj.visual_textual_synergy_score = 80.0
        score_obj.reader_experience_score = 80.0
        calculator.calculate = AsyncMock(return_value=score_obj)
        return calculator

    @pytest.fixture
    def coordinator(self, mock_writer, mock_book_score_calculator):
        return WritingCoordinator(
            writer=mock_writer,
            book_score_calculator=mock_book_score_calculator,
            score_threshold=70.0,
        )

    def test_coordinator_initialization(self, coordinator):
        """Test coordinator initializes with correct defaults."""
        assert coordinator.writer is not None
        assert coordinator.book_score_calculator is not None
        assert coordinator.score_threshold == 70.0

    @pytest.mark.asyncio
    async def test_generate_episodes_pipeline_delegates_to_writer(self, coordinator, mock_writer):
        """Test generate_episodes_pipeline delegates to writer."""
        reporter = MagicMock()
        result = await coordinator.generate_episodes_pipeline(
            book_id=1,
            start_ep=1,
            end_ep=3,
            passion=0.8,
            target_word_count=2000,
            is_easy_mode=True,
            reporter=reporter,
        )
        assert result == (1000, [])
        mock_writer.generate_episodes_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_episodes_delegates_to_writer(self, coordinator, mock_writer):
        """Test generate_episodes delegates to writer."""
        reporter = MagicMock()
        result = await coordinator.generate_episodes(
            book_id=1,
            start_ep=1,
            end_ep=1,
            passion=0.8,
            target_word_count=2000,
            is_easy_mode=True,
            reporter=reporter,
            auto_regenerate=False,
        )
        assert result == 1000
        mock_writer.generate_episodes.assert_called_once()

    def test_audit_generated_text(self, coordinator):
        """Test audit_generated_text executes UnifiedAuditor."""
        text = "「行くぞ！」アルトは叫び、剣を抜いた。夜の風が冷たく吹き抜ける。"
        result = coordinator.audit_generated_text(text)
        assert "quantitative_score" in result
        assert "is_acceptable" in result
        assert "warnings" in result
        assert isinstance(result["warnings"], list)
        assert result["quantitative_score"] > 0

    @pytest.mark.asyncio
    async def test_calculate_book_score_returns_dict(self, coordinator, mock_book_score_calculator):
        """Test calculate_book_score returns expected dict structure."""
        result = await coordinator.calculate_book_score(
            book_id=1,
            chapter_number=1,
            genre="fantasy",
            phase="writing",
        )
        assert result is not None
        assert "overall_score" in result
        assert "structure_score" in result
        assert "regeneration_triggered" in result
        assert "regeneration_actions" in result
        assert result["regeneration_triggered"] is False

    @pytest.mark.asyncio
    async def test_analyze_and_import_chapter_delegates(self, coordinator, mock_writer):
        """Test analyze_and_import_chapter delegates to writer."""
        result = await coordinator.analyze_and_import_chapter(
            book_id=1,
            ep_num=1,
            import_text="手書き原稿",
            do_refine=True,
        )
        assert result == "imported"
        mock_writer.analyze_and_import_chapter.assert_called_once_with(
            book_id=1, ep_num=1, import_text="手書き原稿", do_refine=True
        )

    def test_identify_low_dimensions(self, coordinator):
        """Test _identify_low_dimensions identifies scores below 60."""
        score_obj = MagicMock()
        score_obj.structure_score = 50
        score_obj.coherency_score = 70
        score_obj.factual_grounding_score = 55
        score_obj.visual_textual_synergy_score = 80
        score_obj.reader_experience_score = 90

        low = coordinator._identify_low_dimensions(score_obj)
        assert "structure" in low
        assert "factual_grounding" in low
        assert "coherency" not in low
        assert len(low) == 2

    def test_generate_regeneration_actions(self, coordinator):
        """Test _generate_regeneration_actions creates proper action dicts."""
        actions = coordinator._generate_regeneration_actions(["structure", "coherency"])
        assert len(actions) == 2
        assert actions[0]["dimension"] == "structure"
        assert actions[1]["dimension"] == "coherency"
        assert "target_agent" in actions[0]
        assert "action" in actions[0]
        assert "params" in actions[0]