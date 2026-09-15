import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.context_builder_agent import ContextBuilderAgent

@pytest.mark.asyncio
async def test_context_builder_build():
    agent = ContextBuilderAgent()
    mock_bible = {"world_name": "ファンタジー帝国", "rules": ["魔法が存在する"]}
    mock_chars = [{"name": "アリス", "role": "主人公"}]
    
    ctx = await agent.build_context(
        book_id="b1",
        episode_number=2,
        bible_data=mock_bible,
        characters=mock_chars,
        prev_summary="第1話であらすじ"
    )
    
    assert "ファンタジー帝国" in str(ctx)
    assert "アリス" in str(ctx)
    assert "第1話であらすじ" in str(ctx)
