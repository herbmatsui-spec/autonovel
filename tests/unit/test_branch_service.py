"""
tests/unit/test_branch_service.py - BranchService & What-If Forking Unit Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.branch_service import BranchService
from src.schemas.ux_schemas import BranchCreateRequest, WhatIfRequest
from src.agents.what_if_generator import WhatIfGenerator
from src.shared.domain_event_bus import get_domain_event_bus


@pytest.mark.asyncio
async def test_what_if_generator_cache_key():
    generator = WhatIfGenerator()
    req = WhatIfRequest(
        book_id=1,
        choice_point="秘密の手紙を盗み出す",
        character_name="主人公",
    )
    res = await generator.generate_branch(req)
    assert res.branch_cache_key is not None
    assert len(res.branch_cache_key) > 0
    assert "秘密" in res.alternative_snippet or "運命" in res.alternative_snippet


@pytest.mark.asyncio
async def test_branch_service_create_fork_mock_repo():
    mock_repo = MagicMock()
    mock_repo.create_branch = AsyncMock(return_value=105)

    service = BranchService(branch_repo=mock_repo)

    req = BranchCreateRequest(
        book_id=1,
        parent_branch_id=1,
        fork_ep_num=5,
        new_name="暗殺回避ルート",
        divergence_reason="毒殺を事前に見抜いた",
        what_if_snippet="主人公は怪しい香りに気づき、杯を置いた。",
    )

    received_events = []
    bus = get_domain_event_bus()
    bus.subscribe("BRANCH_FORKED", lambda e: received_events.append(e))

    res = await service.create_fork(req)

    assert res.branch_id == 105
    assert res.book_id == 1
    assert res.name == "暗殺回避ルート"
    assert res.fork_ep_num == 5
    assert res.status == "created"

    mock_repo.create_branch.assert_awaited_once_with(
        book_id=1,
        name="暗殺回避ルート",
        parent_id=1,
        fork_ep_num=5,
        divergence_reason="毒殺を事前に見抜いた",
        what_if_snippet="主人公は怪しい香りに気づき、杯を置いた。",
    )

    # Check event bus
    assert len(received_events) >= 1
    assert received_events[-1].type == "BRANCH_FORKED"
    assert received_events[-1].payload["branch_id"] == 105
