from unittest.mock import AsyncMock

import pytest


# モック化したAIエージェントのテスト
@pytest.mark.anyio
async def test_ai_agent_logic_with_mock():
    # エージェントのモック作成
    mock_agent = AsyncMock()
    mock_agent.process.return_value = {"status": "success", "result": "plot_data"}

    # エージェントの実行
    result = await mock_agent.process("input_data")

    # 検証
    assert result["status"] == "success"
    assert result["result"] == "plot_data"
    mock_agent.process.assert_called_once_with("input_data")
