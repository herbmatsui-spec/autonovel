"""Unit tests for StateGuard."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.domain.writing.state_guard import StateGuard, ValidationResult


class TestStateGuard:
    """Tests for StateGuard."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get_chapters = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def state_guard(self, mock_repo):
        return StateGuard(repo=mock_repo)

    def test_validate_project_context_none(self, state_guard):
        """Test validate_project_context with None input."""
        result = state_guard.validate_project_context(None)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert "プロジェクトコンテキストがNoneです" in result.errors

    def test_validate_project_context_missing_fields(self, state_guard):
        """Test validate_project_context with missing required fields."""
        class EmptyContext:
            pass
        ctx = EmptyContext()
        result = state_guard.validate_project_context(ctx)
        assert result.is_valid is False
        assert any("book_id" in e for e in result.errors)
        assert any("title" in e for e in result.errors)
        assert any("genre" in e for e in result.errors)

    def test_validate_project_context_valid(self, state_guard):
        """Test validate_project_context with valid context."""
        ctx = MagicMock()
        ctx.book_id = 1
        ctx.title = "Test Novel"
        ctx.genre = "fantasy"
        result = state_guard.validate_project_context(ctx)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_project_context_long_title_warning(self, state_guard):
        """Test validate_project_context warns on long title."""
        ctx = MagicMock()
        ctx.book_id = 1
        ctx.title = "A" * 250
        ctx.genre = "fantasy"
        result = state_guard.validate_project_context(ctx)
        assert result.is_valid is True
        assert any("200文字" in w for w in result.warnings)

    def test_validate_project_context_unknown_genre_warning(self, state_guard):
        """Test validate_project_context warns on unknown genre."""
        ctx = MagicMock()
        ctx.book_id = 1
        ctx.title = "Test"
        ctx.genre = "unknown_genre"
        result = state_guard.validate_project_context(ctx)
        assert result.is_valid is True
        assert any("未知のジャンル" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_ensure_chapter_sequence_no_repo(self):
        """Test ensure_chapter_sequence with no repo returns True."""
        guard = StateGuard(repo=None)
        result = await guard.ensure_chapter_sequence(1, 1, 3)
        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_chapter_sequence_valid(self, state_guard, mock_repo):
        """Test ensure_chapter_sequence with valid sequence."""
        mock_repo.get_chapters = AsyncMock(return_value=[])
        result = await state_guard.ensure_chapter_sequence(1, 1, 3)
        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_chapter_sequence_invalid_start(self, state_guard):
        """Test ensure_chapter_sequence with invalid start episode."""
        result = await state_guard.ensure_chapter_sequence(1, 0, 3)
        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_chapter_sequence_end_before_start(self, state_guard):
        """Test ensure_chapter_sequence with end before start."""
        result = await state_guard.ensure_chapter_sequence(1, 5, 3)
        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_chapter_sequence_warns_on_gap(self, state_guard, mock_repo):
        """Test ensure_chapter_sequence warns on gap."""
        existing = [MagicMock(episode_number=1), MagicMock(episode_number=2)]
        mock_repo.get_chapters = AsyncMock(return_value=existing)
        result = await state_guard.ensure_chapter_sequence(1, 5, 7)
        assert result is True  # Still returns True, just warns

    def test_validate_writing_context_empty(self, state_guard):
        """Test validate_writing_context with empty context."""
        result = state_guard.validate_writing_context({})
        assert result.is_valid is False
        assert "執筆コンテキストが空です" in result.errors

    def test_validate_writing_context_missing_keys(self, state_guard):
        """Test validate_writing_context with missing required keys."""
        ctx = {"book_id": 1}
        result = state_guard.validate_writing_context(ctx)
        assert result.is_valid is False
        assert any("ep_num" in e for e in result.errors)
        assert any("plot" in e for e in result.errors)

    def test_validate_writing_context_valid(self, state_guard):
        """Test validate_writing_context with valid context."""
        ctx = {"book_id": 1, "ep_num": 1, "plot": {"summary": "Test plot"}}
        result = state_guard.validate_writing_context(ctx)
        assert result.is_valid is True

    def test_validate_writing_context_empty_plot_warning(self, state_guard):
        """Test validate_writing_context warns on empty plot."""
        ctx = {"book_id": 1, "ep_num": 1, "plot": {}}
        result = state_guard.validate_writing_context(ctx)
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert "空" in result.warnings[0]