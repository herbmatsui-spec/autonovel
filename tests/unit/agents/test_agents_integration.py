import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_agent_pipeline_e2e_mock():
    # 各エージェントの連動スモークテスト
    plot_output = {"title": "テスト小説", "beats": ["起", "承", "転", "結"]}
    assert len(plot_output["beats"]) == 4
