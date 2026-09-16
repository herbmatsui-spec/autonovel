import pytest
from unittest.mock import AsyncMock
from src.agents.plot import PlotAgent

@pytest.mark.asyncio
async def test_plot_agent_generate_beats():
    agent = PlotAgent()
    agent._llm = AsyncMock()
    agent._llm.generate.return_value = '{"beats": [{"act": "Act 1", "summary": "日常と事件の勃発"}]}'

    beats = await agent.generate_plot("学園ファンタジー")
    assert beats is not None
    assert len(beats) >= 1
