
import pytest

from src.backend.workflows.plot_langgraph import PlotGraphManager
from tests.mocks.mock_engine import MockEngine


@pytest.mark.asyncio
async def test_plot_langgraph_workflow(mock_llm):
    # Setup mock LLM responses
    mock_llm.add_json_response("文脈の整理", {"alignment_summary": "Test Summary", "active_subplots": [], "locked_foreshadowings": []})

    engine = MockEngine(mock_llm)
    manager = PlotGraphManager(engine)

    # Run graph
    result = await manager.run(book_id=1, ep_num=1, branch_id=1)

    assert result is not None
    assert result.get("status") == "completed"
    assert "final_plot" in result

    # verify save was called
    assert engine.repo.create_or_replace_plot.called
