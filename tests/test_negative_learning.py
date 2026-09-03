"""Negative Sample Learning Tests"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.learning_data_service import LearningDataService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.misc = MagicMock()
    repo.session = MagicMock()
    return repo


@pytest.fixture
def mock_chroma():
    chroma = MagicMock()
    collection = MagicMock()
    chroma.get_or_create_collection.return_value = collection
    chroma.get_collection.return_value = collection
    return chroma


@pytest.fixture
def learning_service(mock_repo, mock_chroma):
    return LearningDataService(repo=mock_repo, chroma_client=mock_chroma)


@pytest.mark.asyncio
async def test_record_negative_sample_rejected(learning_service, mock_repo, mock_chroma):
    """却下時のネガティブサンプル記録テスト"""
    mock_collection = mock_chroma.get_or_create_collection.return_value
    mock_repo.misc.get_patch_review = AsyncMock(return_value={
        "id": 10,
        "audit_issue_ids": [1, 2],
        "learning_metadata": {
            "negative_sample_candidates": ["logical_consistency", "causal_integrity"],
        },
    })
    mock_repo.session.execute = AsyncMock()

    count = await learning_service.record_negative_sample(
        patch_review_id=10,
        resolution="rejected",
        reviewer_id="editor1",
        comment="This contradiction is intentional for plot twist",
    )

    assert count == 2
    assert mock_collection.add.call_count == 2
    mock_repo.session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_record_negative_sample_approved(learning_service, mock_repo, mock_chroma):
    """承認時のポジティブサンプル記録テスト"""
    mock_collection = mock_chroma.get_or_create_collection.return_value
    mock_repo.misc.get_patch_review = AsyncMock(return_value={
        "id": 11,
        "audit_issue_ids": [3],
        "learning_metadata": {
            "negative_sample_candidates": ["deai"],
        },
    })
    mock_repo.session.execute = AsyncMock()

    count = await learning_service.record_negative_sample(
        patch_review_id=11,
        resolution="approved",
        reviewer_id="editor1",
    )

    assert count == 1
    # label が positive になることを確認
    call_args = mock_collection.add.call_args
    assert call_args[1]["metadatas"][0]["label"] == "positive"


@pytest.mark.asyncio
async def test_record_negative_sample_modified(learning_service, mock_repo, mock_chroma):
    """修正時の両方記録テスト"""
    mock_collection = mock_chroma.get_or_create_collection.return_value
    mock_repo.misc.get_patch_review = AsyncMock(return_value={
        "id": 12,
        "audit_issue_ids": [4],
        "learning_metadata": {
            "negative_sample_candidates": ["ability_consistency"],
        },
    })
    mock_repo.session.execute = AsyncMock()

    count = await learning_service.record_negative_sample(
        patch_review_id=12,
        resolution="modified",
        reviewer_id="editor1",
    )

    assert count == 1
    # modified の場合も positive 扱い
    call_args = mock_collection.add.call_args
    assert call_args[1]["metadatas"][0]["label"] == "positive"


@pytest.mark.asyncio
async def test_get_negative_patterns(learning_service, mock_chroma):
    """ネガティブパターン検索テスト"""
    mock_collection = mock_chroma.get_collection.return_value
    mock_collection.query.return_value = {
        "metadatas": [[
            {"patch_review_id": 10, "audit_type": "logical_consistency", "label": "negative"},
            {"patch_review_id": 11, "audit_type": "logical_consistency", "label": "negative"},
        ]],
    }

    patterns = await learning_service.get_negative_patterns("logical_consistency", limit=10)

    assert len(patterns) == 2
    assert all(p["audit_type"] == "logical_consistency" for p in patterns)
    assert all(p["label"] == "negative" for p in patterns)


@pytest.mark.asyncio
async def test_should_skip_audit_type_many_negatives(learning_service, mock_chroma):
    """ネガティブ多数でスキップ推奨になるテスト"""
    mock_collection = mock_chroma.get_collection.return_value

    # negative 10件, positive 2件
    mock_collection.query.side_effect = [
        # negative patterns
        {"metadatas": [[{"audit_type": "deai"}] for _ in range(10)]},
        # positive patterns
        {"metadatas": [[{"audit_type": "deai"}] for _ in range(2)]},
    ]

    should_skip, conf_adj = await learning_service.should_skip_audit_type("deai")

    assert should_skip is True
    assert conf_adj == -0.3


@pytest.mark.asyncio
async def test_should_skip_audit_type_some_negatives(learning_service, mock_chroma):
    """ネガティブ多めで信頼度下げ推奨テスト"""
    mock_collection = mock_chroma.get_collection.return_value

    # negative 5件, positive 3件
    mock_collection.query.side_effect = [
        {"metadatas": [[{"audit_type": "causal_integrity"}] for _ in range(5)]},
        {"metadatas": [[{"audit_type": "causal_integrity"}] for _ in range(3)]},
    ]

    should_skip, conf_adj = await learning_service.should_skip_audit_type("causal_integrity")

    assert should_skip is False
    assert conf_adj == -0.15


@pytest.mark.asyncio
async def test_should_skip_audit_type_no_patterns(learning_service, mock_chroma):
    """学習データなしでは調整なし"""
    mock_collection = mock_chroma.get_collection.return_value
    mock_collection.query.return_value = {"metadatas": [[]]}

    should_skip, conf_adj = await learning_service.should_skip_audit_type("unknown_type")

    assert should_skip is False
    assert conf_adj == 0.0