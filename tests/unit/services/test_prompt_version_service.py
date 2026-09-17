import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.prompt_version_service import PromptVersionService

@pytest.mark.asyncio
async def test_prompt_version_registration():
    mock_uow = AsyncMock()
    mock_repo = AsyncMock()
    mock_uow.prompt_versions = mock_repo

    # Create a mock version object with id attribute
    mock_version = MagicMock()
    mock_version.id = 1
    mock_version.content = "v1 prompt"
    mock_repo.create_prompt_version.return_value = mock_version
    mock_repo.get_active_prompt_version.return_value = {"content": "v1 prompt"}

    service = PromptVersionService(uow=mock_uow)
    version_id = await service.register_prompt_version(1, "test_prompt", "v1", "v1 prompt")
    assert version_id == 1

    active = await service.get_active_prompt(1, "test_prompt")
    assert active == "v1 prompt"
