"""Unit tests for QualityLoop."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.domain.writing.quality_loop import QualityLoop
from src.domain.writing.models import RegenerationAction
from src.agents.orchestrator import AgentContext, AgentResult


class TestQualityLoop:
    """Tests for QualityLoop."""

    @pytest.fixture
    def mock_writing_agent(self):
        agent = AsyncMock()
        result = AgentResult(
            next_agent=None,
            artifacts={},
            error=None
        )
        result.draft_text = "Test draft"
        agent.execute = AsyncMock(return_value=result)
        return agent

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
    def quality_loop(self, mock_writing_agent, mock_book_score_calculator,
                     mock_context_builder_agent, mock_illustration_agent):
        return QualityLoop(
            writing_agent=mock_writing_agent,
            book_score_calculator=mock_book_score_calculator,
            context_builder_agent=mock_context_builder_agent,
            illustration_agent=mock_illustration_agent,
            compressor=None,
            max_retries=3,
            score_threshold=70.0,
            backoff_base=2.0,
            enable_anti_ai_loop=False,
        )

    def test_quality_loop_initialization(self, quality_loop):
        """Test quality loop initializes with correct defaults."""
        assert quality_loop.writing_agent is not None
        assert quality_loop.book_score_calculator is not None
        assert quality_loop.score_threshold == 70.0
        assert quality_loop.max_retries == 3
        assert quality_loop._enable_anti_ai_loop is False

    @pytest.mark.asyncio
    async def test_evaluate_and_regenerate_returns_on_success(self, quality_loop, mock_writing_agent,
                                                              mock_book_score_calculator):
        """Test evaluate_and_regenerate returns when score meets threshold."""
        ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
        reporter = MagicMock()

        result = await quality_loop.evaluate_and_regenerate(ctx, reporter)

        assert result.error is None
        assert result.draft_text == "Test draft"
        mock_writing_agent.execute.assert_called_once()
        mock_book_score_calculator.calculate.assert_called_once()

    def test_identify_low_dimensions(self, quality_loop):
        """Test _identify_low_dimensions identifies scores below threshold."""
        score_obj = MagicMock()
        score_obj.structure_score = 50
        score_obj.coherency_score = 70
        score_obj.factual_grounding_score = 55
        score_obj.visual_textual_synergy_score = 80
        score_obj.reader_experience_score = 90

        low = quality_loop._identify_low_dimensions(score_obj)
        assert "structure" in low
        assert "factual_grounding" in low
        assert "coherency" not in low
        assert len(low) == 2

    def test_determine_regeneration_action_priority(self, quality_loop):
        """Test _determine_regeneration_action returns highest priority action."""
        # structure has priority 1, coherency has priority 2
        action = quality_loop._determine_regeneration_action(["coherency", "structure"])
        assert isinstance(action, RegenerationAction)
        assert action.focus_dimensions == ["structure"]
        assert action.priority == 1

    def test_determine_regeneration_action_single(self, quality_loop):
        """Test _determine_regeneration_action with single dimension."""
        action = quality_loop._determine_regeneration_action(["reader_experience"])
        assert isinstance(action, RegenerationAction)
        assert action.focus_dimensions == ["reader_experience"]
        assert action.priority == 5