from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.bible_service import WorldBibleGenerator


@pytest.mark.asyncio
async def test_bible_service_apply_manual_setting_change_not_found():
    repo = MagicMock()
    llm = MagicMock()
    pm = MagicMock()
    debate = MagicMock()
    marketing = MagicMock()
    auditor = MagicMock()

    service = WorldBibleGenerator(repo, llm, pm, debate, marketing, auditor)
    repo.bible.get_bible = AsyncMock(return_value=None)

    result = await service.apply_manual_setting_change(
        book_id=1, field_path="title", new_value="New Title"
    )
    assert result is False


@pytest.mark.asyncio
async def test_bible_service_apply_manual_setting_change_unchanged():
    repo = MagicMock()
    service = WorldBibleGenerator(repo, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())

    dummy_bible = {"title": "Same Title"}
    repo.bible.get_bible = AsyncMock(return_value=dummy_bible)

    result = await service.apply_manual_setting_change(
        book_id=1, field_path="title", new_value="Same Title"
    )
    assert result is True
    repo.save_full_world_bible.assert_not_called()


@pytest.mark.asyncio
async def test_bible_service_apply_manual_setting_change_success():
    repo = MagicMock()
    service = WorldBibleGenerator(repo, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())

    dummy_bible = {"title": "Old Title"}
    repo.bible.get_bible = AsyncMock(return_value=dummy_bible)
    repo.save_full_world_bible = AsyncMock()
    repo.misc.create_setting_delta = AsyncMock(return_value=123)
    service.create_setting_snapshot = AsyncMock(return_value=456)

    result = await service.apply_manual_setting_change(
        book_id=1, field_path="title", new_value="Brand New Title", user_id="user_1"
    )
    assert result is True
    assert dummy_bible["title"] == "Brand New Title"
    repo.save_full_world_bible.assert_called_once_with(dummy_bible, book_id=1)
    service.create_setting_snapshot.assert_called_once()
