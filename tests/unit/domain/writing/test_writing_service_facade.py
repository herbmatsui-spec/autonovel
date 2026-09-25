"""Unit tests for WritingService facade."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.domain.writing import WritingService, WritingCoordinator, QualityLoop, StateGuard, ValidationResult
from src.domain.writing.models import WritingGenerationContext, RegenerationAction
from src.agents.orchestrator import AgentContext, AgentResult


class TestWritingServiceFacade:
    """Tests for WritingService facade."""

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
    def mock_context_builder_agent(self):
        agent = AsyncMock()
        result = AgentResult(
            next_agent=None,
            artifacts={"writing_context": {}},
            error=None
        )
        agent.execute = AsyncMock(return_value=result)
        return agent

    @pytest.fixture
    def mock_illustration_agent(self):
        return AsyncMock()

    @pytest.fixture
    def writing_service(self, mock_writer, mock_book_score_calculator,
                        mock_context_builder_agent, mock_illustration_agent):
        return WritingService(
            writer=mock_writer,
            repo=MagicMock(),
            book_score_calculator=mock_book_score_calculator,
            writing_agent=mock_writer,
            context_builder_agent=mock_context_builder_agent,
            illustration_agent=mock_illustration_agent,
            compressor=None,
            max_retries=3,
            score_threshold=70.0,
            backoff_base=2.0,
            enable_anti_ai_loop=False,
        )

    def test_facade_initialization(self, writing_service):
        """Test facade initializes all sub-components."""
        assert writing_service._coordinator is not None
        assert writing_service._quality_loop is not None
        assert writing_service._state_guard is not None
        assert isinstance(writing_service._coordinator, WritingCoordinator)
        assert isinstance(writing_service._quality_loop, QualityLoop)
        assert isinstance(writing_service._state_guard, StateGuard)

    def test_facade_reexports_models(self, writing_service):
        """Test facade re-exports shared models."""
        assert hasattr(writing_service, "WritingGenerationContext")
        assert hasattr(writing_service, "clean_writing_response")
        assert hasattr(writing_service, "RegenerationAction")
        assert hasattr(writing_service, "DIMENSION_ACTIONS")

    @pytest.mark.asyncio
    async def test_generate_episodes_pipeline_delegates(self, writing_service, mock_writer):
        """Test generate_episodes_pipeline delegates to coordinator."""
        reporter = MagicMock()
        result = await writing_service.generate_episodes_pipeline(
            book_id=1, start_ep=1, end_ep=3, passion=0.8,
            target_word_count=2000, is_easy_mode=True, reporter=reporter
        )
        assert result == (1000, [])
        mock_writer.generate_episodes_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_episodes_delegates(self, writing_service, mock_writer):
        """Test generate_episodes delegates to coordinator."""
        reporter = MagicMock()
        result = await writing_service.generate_episodes(
            book_id=1, start_ep=1, end_ep=1, passion=0.8,
            target_word_count=2000, is_easy_mode=True, reporter=reporter,
            auto_regenerate=False
        )
        assert result == 1000
        mock_writer.generate_episodes.assert_called_once()

    def test_audit_generated_text_delegates(self, writing_service):
        """Test audit_generated_text delegates to coordinator."""
        text = "Test text"
        result = writing_service.audit_generated_text(text)
        assert "quantitative_score" in result
        assert "is_acceptable" in result

    @pytest.mark.asyncio
    async def test_calculate_book_score_delegates(self, writing_service, mock_book_score_calculator):
        """Test calculate_book_score delegates to coordinator."""
        result = await writing_service.calculate_book_score(
            book_id=1, chapter_number=1, genre="fantasy", phase="writing"
        )
        assert result is not None
        assert "overall_score" in result
        mock_book_score_calculator.calculate.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_and_import_chapter_delegates(self, writing_service, mock_writer):
        """Test analyze_and_import_chapter delegates to coordinator."""
        result = await writing_service.analyze_and_import_chapter(
            book_id=1, ep_num=1, import_text="text", do_refine=True
        )
        assert result == "imported"
        mock_writer.analyze_and_import_chapter.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_quality_assurance_delegates(self, writing_service, mock_writer):
        """Test generate_with_quality_assurance delegates to quality_loop."""
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        result = await writing_service.generate_with_quality_assurance(ctx)
        # Just verify the method was called - the actual result depends on mock setup
        mock_writer.execute.assert_called()

    def test_validate_project_context_delegates(self, writing_service):
        """Test validate_project_context delegates to state_guard."""
        ctx = MagicMock()
        ctx.book_id = 1
        ctx.title = "Test"
        ctx.genre = "fantasy"
        result = writing_service.validate_project_context(ctx)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_ensure_chapter_sequence_delegates(self, writing_service):
        """Test ensure_chapter_sequence delegates to state_guard."""
        # Mock the repo's get_chapters to return empty list
        writing_service._state_guard.repo.get_chapters = AsyncMock(return_value=[])
        result = await writing_service.ensure_chapter_sequence(1, 1, 3)
        assert result is True

    def test_validate_writing_context_delegates(self, writing_service):
        """Test validate_writing_context delegates to state_guard."""
        ctx = {"book_id": 1, "ep_num": 1, "plot": {"summary": "Test"}}
        result = writing_service.validate_writing_context(ctx)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    def test_backward_compatibility_aliases(self):
        """Test WritingServices alias exists."""
        from src.domain.writing import WritingServices
        assert WritingServices is WritingService