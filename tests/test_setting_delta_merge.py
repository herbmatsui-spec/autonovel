"""Setting Delta Merge and GraphRAG Sync Tests"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.bible_service import WorldBibleGenerator
from src.services.graphrag_sync_service import GraphRAGSyncService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.misc = MagicMock()
    repo.bible = MagicMock()
    repo.session = MagicMock()
    return repo


@pytest.fixture
def bible_generator(mock_repo):
    return WorldBibleGenerator(
        repo=mock_repo,
        llm=MagicMock(),
        pm=MagicMock(),
        debate=MagicMock(),
        marketing=MagicMock(),
        auditor=MagicMock(),
    )


@pytest.mark.asyncio
async def test_record_setting_delta(bible_generator, mock_repo):
    """設定変更差分記録のテスト"""
    mock_repo.misc.create_setting_delta = AsyncMock(return_value=5)

    delta_id = await bible_generator.record_setting_delta(
        book_id=1,
        field_path="world_rules.magic_system.mana_cost",
        old_value="10",
        new_value="15",
        delta_type="MANUAL",
        source="user",
    )

    assert delta_id == 5
    mock_repo.misc.create_setting_delta.assert_called_once_with(
        book_id=1,
        field_path="world_rules.magic_system.mana_cost",
        old_value="10",
        new_value="15",
        delta_type="MANUAL",
        source="user",
        patch_review_id=None,
    )


@pytest.mark.asyncio
async def test_create_setting_snapshot(bible_generator, mock_repo):
    """設定スナップショット作成のテスト"""
    mock_bible = MagicMock()
    mock_bible.model_dump.return_value = {"title": "Test", "world_rules": {}}
    mock_repo.bible.get_bible = AsyncMock(return_value=mock_bible)
    mock_repo.misc.create_setting_version = AsyncMock(return_value=3)
    mock_repo.session.execute = AsyncMock()

    version_id = await bible_generator.create_setting_snapshot(
        book_id=1,
        change_summary="Updated mana cost",
        created_by="user1",
    )

    assert version_id == 3
    mock_repo.misc.create_setting_version.assert_called_once()


@pytest.mark.asyncio
async def test_apply_manual_setting_change(bible_generator, mock_repo):
    """手動設定変更適用のテスト"""
    mock_bible = MagicMock()
    mock_bible.world_rules = MagicMock()
    mock_bible.world_rules.magic_system = {"mana_cost": 10}
    mock_repo.bible.get_bible = AsyncMock(return_value=mock_bible)
    mock_repo.save_full_world_bible = AsyncMock()
    mock_repo.misc.create_setting_delta = AsyncMock(return_value=7)
    mock_repo.misc.create_setting_version = AsyncMock(return_value=4)

    success = await bible_generator.apply_manual_setting_change(
        book_id=1,
        field_path="world_rules.magic_system.mana_cost",
        new_value=15,
        user_id="user1",
    )

    assert success is True
    assert mock_bible.world_rules.magic_system["mana_cost"] == 15
    mock_repo.save_full_world_bible.assert_called_once()
    mock_repo.misc.create_setting_delta.assert_called_once()
    mock_repo.misc.create_setting_version.assert_called_once()


@pytest.mark.asyncio
async def test_apply_manual_setting_change_no_change(bible_generator, mock_repo):
    """値が変わらない場合はスキップされることを確認"""
    mock_bible = MagicMock()
    mock_bible.world_rules = MagicMock()
    mock_bible.world_rules.magic_system = {"mana_cost": 15}
    mock_repo.bible.get_bible = AsyncMock(return_value=mock_bible)

    success = await bible_generator.apply_manual_setting_change(
        book_id=1,
        field_path="world_rules.magic_system.mana_cost",
        new_value=15,  # 同じ値
        user_id="user1",
    )

    assert success is True
    mock_repo.save_full_world_bible.assert_not_called()


@pytest.mark.asyncio
async def test_graphrag_sync_service_merge_delta():
    """GraphRAG への差分マージテスト"""
    mock_repo = MagicMock()
    mock_chroma = MagicMock()
    mock_collection = MagicMock()
    mock_chroma.get_collection.return_value = mock_collection

    mock_repo.misc.get_setting_delta = AsyncMock(return_value={
        "id": 1,
        "book_id": 1,
        "field_path": "world_rules.magic_system.mana_cost",
        "new_value": "15",
        "source": "user",
        "delta_type": "MANUAL",
        "merged_to_graphrag": False,
    })
    mock_repo.misc.mark_delta_merged = AsyncMock()

    service = GraphRAGSyncService(repo=mock_repo, chroma_client=mock_chroma)

    result = await service.merge_setting_delta(1)

    assert result is True
    mock_collection.delete.assert_called_once()
    mock_collection.add.assert_called_once()
    mock_repo.misc.mark_delta_merged.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_graphrag_sync_service_already_merged():
    """既にマージ済みの差分はスキップされることを確認"""
    mock_repo = MagicMock()
    mock_repo.misc.get_setting_delta = AsyncMock(return_value={
        "id": 1,
        "merged_to_graphrag": True,
    })

    service = GraphRAGSyncService(repo=mock_repo)

    result = await service.merge_setting_delta(1)

    assert result is True
    mock_repo.misc.mark_delta_merged.assert_not_called()


@pytest.mark.asyncio
async def test_graphrag_reindex_book_settings():
    """書籍設定の全再インデックステスト"""
    mock_repo = MagicMock()
    mock_chroma = MagicMock()
    mock_collection = MagicMock()
    mock_chroma.get_or_create_collection.return_value = mock_collection

    mock_bible = MagicMock()
    mock_bible.model_dump.return_value = {
        "title": "Test Novel",
        "world_rules": {"magic_system": {"mana_cost": 15}},
        "characters": [{"name": "Hero"}],
    }
    mock_repo.bible.get_bible = AsyncMock(return_value=mock_bible)

    service = GraphRAGSyncService(repo=mock_repo, chroma_client=mock_chroma)

    result = await service.reindex_book_settings(1)

    assert result is True
    mock_collection.delete.assert_called_once()
    assert mock_collection.add.call_count >= 2  # title + world_rules + characters