import pytest
import asyncio
from unittest import mock
from autonovel.src.agents.illustration_agent import IllustrationAgent
from autonovel.src.models.illustration import IllustrationType, IllustrationModel, SafetyLevel

@pytest.mark.asyncio
async def test_illustration_agent_prompt_generation():
    # Mock dependencies
    mock_llm = mock.AsyncMock()
    mock_llm.generate.return_value = "A beautiful fantasy landscape with a floating castle."
    
    _ = mock.AsyncMock()
    agent = IllustrationAgent(llm=mock_llm, image_service=_ )
    
    # Test cover prompt generation
    book_context = {
        "title": "天空の城",
        "genre": "ファンタジー",
        "concept": "空に浮かぶ城を舞台にした冒険譚"
    }
    
    # In the current implementation, logic is inside _generate_cover / _generate_episode_illustration
    # We test run() with a mock request
    from autonovel.src.models.illustration import IllustrationRequest
    request = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.COVER,
        model=IllustrationModel.QUALITY,
        safety_level=SafetyLevel.BLOCK_SOME
    )
    result = await agent.run(request=request)
    
    assert result["status"] == "success"
    assert result["result"].image_url is not None

@pytest.mark.asyncio
async def test_illustration_agent_erotic_mode_modifier():
    mock_llm = mock.AsyncMock()
    mock_llm.generate.return_value = "A romantic scene in a moonlit bedroom."
    
    mock_service = mock.AsyncMock()
    agent = IllustrationAgent(llm=mock_llm, image_service=mock_service)
    
    book_context = {
        "title": "禁断の恋",
        "genre": "官能",
        "concept": "秘めた想いが爆発する一夜"
    }
    
    # Test R15 modifier
    from autonovel.src.models.illustration import IllustrationRequest
    request = IllustrationRequest(
        book_id=1,
        episode_number=1,
        illustration_type=IllustrationType.EPISODE,
        model=IllustrationModel.QUALITY,
        safety_level=SafetyLevel.R15_CONTENT
    )
    result = await agent.run(request=request)
    
    assert result["status"] == "success"
    # Check if the resulting prompt contains R15 keywords (since we didn't use LLM mock for the actual prompt in this version)
    prompt = result["result"].prompt
    assert any(word in prompt.lower() for word in ["r15", "artistic", "intimate"])
