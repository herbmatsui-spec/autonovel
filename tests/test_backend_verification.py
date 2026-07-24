import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from tests.mocks.test_harness import BackendTestHarness
from src.backend.routers.plots import get_plots
from src.backend.routers.episodes import get_chapters
from fastapi import Request

# Mock Request for FastAPI endpoints
class MockRequest:
    def __init__(self, scope=None):
        self.scope = scope or {}

@pytest.fixture
def harness():
    return BackendTestHarness()

@pytest.mark.asyncio
async def test_get_plots_success(harness):
    # Setup: Create a book and some plots
    book_id = 1
    plot_data = [
        {"ep_num": 1, "title": "Start", "summary": "Intro", "detailed_blueprint": "BP1", "tension": 10, "is_catharsis": False, "status": "completed"},
        {"ep_num": 2, "title": "Middle", "summary": "Conflict", "detailed_blueprint": "BP2", "tension": 50, "is_catharsis": False, "status": "completed"},
    ]
    await harness.setup_scenario(book_id, plot_data=plot_data)

    # Mock UnitOfWork context manager to use the harness's mock UOW
    with patch("src.backend.routers.plots.UnitOfWork", return_value=harness.uow):
        with patch("src.backend.routers.plots.Container") as mock_container:
            mock_container.db.return_value = MagicMock()
            
            # The harness's MockUnitOfWork needs to handle the specific method called in the router
            # In routers/plots.py: await uow.plots.get_all_plots(book_id)
            # Our MockPlotRepository currently has get_plots. Let's add get_all_plots or mock it.
            harness.uow.plots.get_all_plots = AsyncMock(return_value=[
                MagicMock(ep_num=1, title="Start", summary="Intro", detailed_blueprint="BP1", tension=10, is_catharsis=False, status="completed"),
                MagicMock(ep_num=2, title="Middle", summary="Conflict", detailed_blueprint="BP2", tension=50, is_catharsis=False, status="completed"),
            ])

            results = await get_plots(book_id)
            
            assert len(results) == 2
            assert results[0]["ep_num"] == 1
            assert results[1]["tension"] == 50

@pytest.mark.asyncio
async def test_get_chapters_success(harness):
    # Setup: Create a book and some chapters
    book_id = 1
    chapter_data = [
        {"ep_num": 1, "title": "Ch1", "content": "Content 1", "summary": "Sum 1", "created_at": "2023-01-01"},
    ]
    await harness.setup_scenario(book_id, chapter_data=chapter_data)

    with patch("src.backend.routers.episodes.UnitOfWork", return_value=harness.uow):
        with patch("src.backend.routers.episodes.Container") as mock_container:
            mock_container.db.return_value = MagicMock()
            
            # In routers/episodes.py: await uow.chapters.get_all_non_anchor_chapters(book_id)
            harness.uow.chapters.get_all_non_anchor_chapters = AsyncMock(return_value=[
                MagicMock(ep_num=1, title="Ch1", content="Content 1", summary="Sum 1", created_at="2023-01-01")
            ])

            results = await get_chapters(book_id)
            
            assert len(results) == 1
            assert results[0]["title"] == "Ch1"
            assert results[0]["content"] == "Content 1"

@pytest.mark.asyncio
async def test_api_auth_failure():
    from src.backend.auth import validate_api_key_or_raise
    from src.backend.auth import AppError
    
    with pytest.raises(AppError) as excinfo:
         validate_api_key_or_raise("invalid_key")
    
    assert "API キーが無効です" in str(excinfo.value)

@pytest.mark.asyncio
async def test_expand_plots_success(harness):
    from src.backend.routers.plots import expand_plots
    from src.models.api_schemas import PlotExpandRequest
    
    # Setup
    book_id = 1
    req = PlotExpandRequest(
        api_key="valid_key",
        book_id=book_id,
        gen_from=1,
        gen_to=2,
        config={"model": "gemini-pro"},
        params={"style": "detailed"}
    )
    await harness.setup_scenario(book_id)
    
    # Mock the task execution to avoid running the actual workflow
    with patch("src.backend.tasks.execute_service_workflow") as mock_execute:
        with patch("src.backend.routers.plots._create_task", new_callable=AsyncMock) as mock_create_task:
            mock_create_task.return_value = None
            
            result = await expand_plots(req)
            
            assert "task_id" in result
            assert result["task_id"].startswith("plot_expand_")
            mock_execute.assert_called_once()
            
            # Verify the workflow call
            args, kwargs = mock_execute.call_args
            assert kwargs["method_name"] == "plot_expansion_workflow"
            assert kwargs["kwargs"]["book_id"] == book_id
            assert kwargs["kwargs"]["mode"] == "final"

@pytest.mark.asyncio
async def test_expand_plots_auth_failure(harness):
    from src.backend.routers.plots import expand_plots
    from src.models.api_schemas import PlotExpandRequest
    from src.backend.auth import AppError
    
    # Setup: use an invalid key
    req = PlotExpandRequest(
        api_key="invalid_key",
        book_id=1,
        gen_from=1,
        gen_to=2,
        config={},
        params={}
    )
    
    with pytest.raises(AppError) as excinfo:
        await expand_plots(req)
    
    assert "API キーが無効です" in str(excinfo.value)
