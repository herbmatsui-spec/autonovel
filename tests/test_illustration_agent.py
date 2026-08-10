from unittest import mock

import pytest
from autonovel.src.agents.illustration_agent import IllustrationAgent
from autonovel.src.models.illustration import (
    IllustrationModel,
    IllustrationRequest,
    IllustrationType,
    SafetyLevel,
)


@pytest.mark.asyncio
async def test_illustration_agent_prompt_generation():
    mock_llm = mock.AsyncMock()
    mock_llm.generate.return_value = "A beautiful fantasy landscape with a floating castle."

    mock_service = mock.AsyncMock()
    mock_service.generate.return_value = "/static/illustrations/fake.png"
    agent = IllustrationAgent(llm=mock_llm, image_service=mock_service)

    request = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.COVER,
        model=IllustrationModel.QUALITY,
        safety_level=SafetyLevel.BLOCK_SOME,
        book_context={
            "title": "天空の城",
            "genre": "ファンタジー",
            "concept": "空に浮かぶ城を舞台にした冒険譚",
        },
    )
    result = await agent.run(request=request)

    assert result["status"] == "success"
    assert result["result"].image_url == "/static/illustrations/fake.png"


@pytest.mark.asyncio
async def test_illustration_agent_erotic_mode_modifier():
    mock_llm = mock.AsyncMock()
    mock_llm.generate.return_value = "A romantic scene in a moonlit bedroom."

    mock_service = mock.AsyncMock()
    agent = IllustrationAgent(llm=mock.AsyncMock(), image_service=mock_service)

    request = IllustrationRequest(
        book_id=1,
        episode_number=1,
        illustration_type=IllustrationType.EPISODE,
        model=IllustrationModel.QUALITY,
        safety_level=SafetyLevel.R15_CONTENT,
    )
    result = await agent.run(request=request)

    assert result["status"] == "success"
    # Check if the resulting prompt contains R15 keywords (since we didn't use LLM mock for the actual prompt in this version)
    prompt = result["result"].prompt
    assert any(word in prompt.lower() for word in ["r15", "artistic", "intimate"])


@pytest.mark.asyncio
async def test_illustration_agent_auto_model_resolves():
    mock_service = mock.AsyncMock()
    mock_service.generate.return_value = "/static/illustrations/fake.png"
    agent = IllustrationAgent(llm=mock.AsyncMock(), image_service=mock_service)

    request = IllustrationRequest(
        book_id=1,
        illustration_type=IllustrationType.COVER,
        model=IllustrationModel.AUTO,
        book_context={"title": "Test", "genre": "ファンタジー"},
    )
    result = await agent.run(request=request)

    assert result["status"] == "success"
    assert result["result"].model_used == "imagen-4.0-ultra-generate-001"
