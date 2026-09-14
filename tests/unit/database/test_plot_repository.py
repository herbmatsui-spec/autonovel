import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.plot import PlotRepository
from src.backend.database.models import Plot

@pytest.mark.asyncio
async def test_plot_repository_save_and_fetch():
    mock_session = AsyncMock()
    # Create a Plot with all required fields for PlotDbModel
    mock_plot = Plot(
        id=1, 
        book_id=1, 
        branch_id=1, 
        ep_num=1, 
        title="Test Plot", 
        status="expanded",
        thought_process="",
        summary="",
        one_line_summary="",
        detailed_blueprint="",
        tension=50,
        tension_delta=0,
        catharsis=0,
        scenes="[]",
        is_catharsis=False,
        catharsis_type="なし",
        love_meter=0,
        next_hook="{}",
        misunderstanding_gap="",
        lite_model_director_notes="",
        script_content="",
        current_chain_phase="Friction",
        resolution_style="Cheat",
        burned_cost_or_loot="なし",
        antagonist_status="現状維持",
        thematic_milestone="なし",
        state_integrity_score=100,
        emotional_resonance_score=0,
        thematic_depth_score=0,
        literary_beauty_score=0,
        erotic_intensity=0,
        healed_fields="[]",
        is_micro_catharsis=False,
        information_asymmetry_level=0.0,
        cost_score=0.0,
        qol_delta=0,
        discovery_item="",
        sanctuary_event="",
        is_locked=False,
        is_simulation=False,
        simulation_id=""
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_plot
    mock_session.execute.return_value = mock_result
    
    repo = PlotRepository(mock_session)
    plot = await repo.get_plot(book_id_or_branch_id=1, ep_num=1)
    assert plot is not None