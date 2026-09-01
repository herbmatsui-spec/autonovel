from unittest import mock

import pytest

from src.agents.illustration_agent import IllustrationAgent
from src.models.illustration import (
    IllustrationModel,
    IllustrationRequest,
    IllustrationResult,
    IllustrationType,
    SafetyLevel,
)


@pytest.mark.asyncio
async def test_illustration_agent_cover_generation():
    """Cover タイプ: image_service.generate が呼ばれ、正常 URL が返ることを検証。"""
    mock_llm = mock.AsyncMock()
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
    mock_service.generate.assert_called_once()


@pytest.mark.asyncio
async def test_illustration_agent_episode_r15_prompt_contains_r15():
    """EPISODE + R15_CONTENT: 画像生成プロンプトに R15 キーワードが含まれることを検証。"""
    mock_llm = mock.AsyncMock()
    mock_service = mock.AsyncMock()
    mock_service.generate.return_value = "/static/illustrations/erotic_scene.png"
    agent = IllustrationAgent(llm=mock_llm, image_service=mock_service)

    request = IllustrationRequest(
        book_id=1,
        episode_number=1,
        illustration_type=IllustrationType.EPISODE,
        model=IllustrationModel.QUALITY,
        safety_level=SafetyLevel.R15_CONTENT,
    )
    result = await agent.run(request=request)

    assert result["status"] == "success"
    prompt = result["result"].prompt
    assert "r15" in prompt.lower(), f"Expected 'r15' in prompt, got: {prompt}"
    mock_service.generate.assert_called_once()


@pytest.mark.asyncio
async def test_illustration_agent_auto_model_resolves():
    """AUTO モデル解決: model_used が期待値と一致することを検証。"""
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
    mock_service.generate.assert_called_once()
