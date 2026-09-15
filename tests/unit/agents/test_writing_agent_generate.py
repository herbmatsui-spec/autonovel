import pytest
from unittest.mock import AsyncMock
from src.agents.writing._writing import execute_writing_generation

@pytest.mark.asyncio
async def test_execute_writing_generation():
    mock_llm = AsyncMock()
    mock_llm.stream.return_value = ["扉が開いた。", "目の前にいたのは騎士だった。"]
    
    result = await execute_writing_generation(
        llm=mock_llm,
        prompt="執筆開始",
        max_tokens=500
    )
    assert "扉が開いた。" in result
    assert "騎士だった。" in result
