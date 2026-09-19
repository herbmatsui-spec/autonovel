"""Integration unit tests for ForeshadowingService ensemble judgment."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from src.models.writing_metadata import WritingMetadata, ForeshadowingReport
from src.services.foreshadowing_service import ForeshadowingService


@dataclass
class DummyForeshadowing:
    id: int
    book_id: int
    title: str
    target_episode: int
    status: str = "planted"
    keywords: list[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@pytest.mark.asyncio
async def test_ensemble_check_and_resolve_success():
    """Verify that contracted item with resolved metadata is resolved."""
    mock_repo = MagicMock()
    mock_repo.get_unresolved = AsyncMock(
        return_value=[
            DummyForeshadowing(
                id=10,
                book_id=1,
                title="古いペンダント",
                target_episode=5,
                keywords=["ペンダント"],
            )
        ]
    )
    mock_repo.resolve = AsyncMock(return_value=True)
    mock_repo.progress = AsyncMock()

    service = ForeshadowingService(mock_repo)

    metadata = WritingMetadata(
        episode_number=5,
        foreshadowings=[
            ForeshadowingReport(
                foreshadowing_id=10,
                action="resolved",
                rationale="ペンダントが砕け散った",
                excerpt="ペンダントが砕け散った。",
            )
        ],
    )

    resolved = await service.check_and_resolve(
        book_id=1,
        episode_num=5,
        draft_text="激戦の末、古いペンダントが砕け散った。",
        writing_metadata=metadata,
        contract_ids=[10],
    )

    assert "古いペンダント" in resolved
    mock_repo.resolve.assert_awaited_once_with(10, 5)


@pytest.mark.asyncio
async def test_ensemble_prevents_accidental_keyword_mention():
    """Verify that accidental keyword mention without contract/metadata does NOT resolve."""
    mock_repo = MagicMock()
    mock_repo.get_unresolved = AsyncMock(
        return_value=[
            DummyForeshadowing(
                id=20,
                book_id=1,
                title="賢者の手紙",
                target_episode=20,  # Scheduled for ep 20, not ep 5
                keywords=["手紙"],
            )
        ]
    )
    mock_repo.resolve = AsyncMock(return_value=True)

    service = ForeshadowingService(mock_repo)

    # In ep 5, character casually mentions "手紙"
    resolved = await service.check_and_resolve(
        book_id=1,
        episode_num=5,
        draft_text="彼は机の上にあった手紙を見た。",
        writing_metadata=None,  # No metadata self-report
        contract_ids=[],        # Not in ep 5 contract
    )

    assert resolved == []
    mock_repo.resolve.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensemble_reschedules_unfulfilled_contract():
    """Verify that a contracted item not resolved gets rescheduled."""
    mock_repo = MagicMock()
    mock_repo.get_unresolved = AsyncMock(
        return_value=[
            DummyForeshadowing(
                id=30,
                book_id=1,
                title="裏切り者の正体",
                target_episode=5,  # Contracted for ep 5
                keywords=["裏切り者"],
            )
        ]
    )
    mock_repo.progress = AsyncMock()
    mock_repo.update_target_episode = AsyncMock()

    service = ForeshadowingService(mock_repo)

    metadata = WritingMetadata(
        episode_number=5,
        foreshadowings=[
            ForeshadowingReport(
                foreshadowing_id=30,
                action="progressed",
                rationale="Only a shadow was seen",
            )
        ],
    )

    resolved = await service.check_and_resolve(
        book_id=1,
        episode_num=5,
        draft_text="主人公は裏切り者の影に気づいた。",
        writing_metadata=metadata,
        contract_ids=[30],
    )

    assert resolved == []
    mock_repo.progress.assert_awaited_once_with(30)
    mock_repo.update_target_episode.assert_awaited_once()
