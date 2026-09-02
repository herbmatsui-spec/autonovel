from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.prompt_version_service import PromptVersionService


@pytest.mark.asyncio
async def test_register_prompt_version():
    """PromptVersionService でのバージョン登録の検証。"""
    mock_uow = MagicMock()
    mock_prompt_repo = AsyncMock()
    mock_version = MagicMock()
    mock_version.id = 101
    mock_prompt_repo.create_prompt_version.return_value = mock_version
    mock_uow.prompt_versions = mock_prompt_repo
    mock_uow.commit = AsyncMock()
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None

    service = PromptVersionService(uow=mock_uow)
    version_id = await service.register_prompt_version(
        book_id=1,
        prompt_key="writer_prompt",
        version_tag="v1.0",
        content="Write novel...",
        is_active=True,
    )

    assert version_id == 101
    assert mock_prompt_repo.set_active_prompt_version.called
    assert mock_prompt_repo.create_prompt_version.called
    assert mock_uow.commit.called


@pytest.mark.asyncio
async def test_get_active_prompt():
    """アクティブなプロンプトの取得検証。"""
    mock_uow = MagicMock()
    mock_prompt_repo = AsyncMock()
    mock_prompt_repo.get_active_prompt_version.return_value = {"content": "Active prompt content"}
    mock_uow.prompt_versions = mock_prompt_repo
    mock_uow.__aenter__.return_value = mock_uow
    mock_uow.__aexit__.return_value = None

    service = PromptVersionService(uow=mock_uow)
    content = await service.get_active_prompt(book_id=1, prompt_key="writer_prompt")

    assert content == "Active prompt content"
