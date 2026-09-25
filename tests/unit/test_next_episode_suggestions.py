"""tests/unit/test_next_episode_suggestions.py - 次話AI展開提案の単体テスト."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.editor import BranchType, NextBeatsRequest
from src.services.next_beats_service import NextBeatsService


@pytest.mark.asyncio
async def test_generate_three_beats_success():
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(
        return_value='{"title": "逆転の一撃", "summary": "主人公の覚醒", "content": "剣が眩い光を放った。", "hook_text": "その先で待っていたのは……"}'
    )

    service = NextBeatsService(llm_gateway=mock_llm)
    req = NextBeatsRequest(
        book_id=1,
        current_text="主人公は絶体絶命の危機に瀕していた。",
        genre="ハイファンタジー (R15)",
    )

    response = await service.generate_three_beats(req)

    assert len(response.beats) == 3
    types = [b.branch_type for b in response.beats]
    assert BranchType.ROYAL in types
    assert BranchType.TWIST in types
    assert BranchType.PSYCHOLOGY in types

    for card in response.beats:
        assert card.card_id is not None
        assert card.title != ""
        assert card.content != ""
