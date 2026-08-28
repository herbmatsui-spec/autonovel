"""
tests/integration/test_what_if_and_hitl_orchestration.py - End-to-End orchestration test for What-If branching and HITL
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.what_if_generator import WhatIfGenerator
from src.services.branch_service import BranchService
from src.schemas.ux_schemas import WhatIfRequest, BranchCreateRequest
from src.backend.hitl_manager import HITLManager
from src.backend.workflows.graphs.master_graph import compile_master_graph
from src.backend.workflows.state import MasterGraphState
from src.shared.domain_event_bus import NarrativeEventType, get_domain_event_bus


@pytest.mark.asyncio
async def test_what_if_forking_and_hitl_orchestration():
    # 1. Setup EventBus listening
    bus = get_domain_event_bus()
    events_log = []
    bus.subscribe(NarrativeEventType.BRANCH_FORKED, lambda e: events_log.append(("BRANCH_FORKED", e)))
    bus.subscribe(NarrativeEventType.HITL_SUSPENDED, lambda e: events_log.append(("HITL_SUSPENDED", e)))
    bus.subscribe(NarrativeEventType.HITL_RESUMED, lambda e: events_log.append(("HITL_RESUMED", e)))

    # 2. Generate What-If Route
    what_if_gen = WhatIfGenerator()
    what_if_req = WhatIfRequest(
        book_id=1,
        choice_point="魔王軍の使者と極秘会談を行う",
        character_name="主人公",
    )
    what_if_res = await what_if_gen.generate_branch(what_if_req)
    assert what_if_res.branch_cache_key is not None
    assert what_if_res.alternative_snippet is not None

    # 3. Fork into a new Branch
    mock_repo = MagicMock()
    mock_repo.create_branch = AsyncMock(return_value=201)

    branch_service = BranchService(branch_repo=mock_repo)
    fork_req = BranchCreateRequest(
        book_id=1,
        parent_branch_id=1,
        fork_ep_num=2,
        new_name="魔王軍同盟ルート",
        divergence_reason="極秘会談を通じて一時休戦協定を結んだ",
        what_if_snippet=what_if_res.alternative_snippet,
    )
    fork_res = await branch_service.create_fork(fork_req)
    assert fork_res.branch_id == 201
    assert fork_res.name == "魔王軍同盟ルート"

    # Verify event emitted
    assert any(ev[0] == "BRANCH_FORKED" for ev in events_log)

    # 4. Run MasterGraph on the new branch with HITL enabled
    hitl_manager = HITLManager()
    master_app = compile_master_graph()

    master_input: MasterGraphState = {
        "task_id": "test-orchestration-001",
        "book_id": 1,
        "active_branch_id": fork_res.branch_id,
        "target_start_ep": 3,
        "target_end_ep": 3,
        "enable_hitl": True,
        "hitl_timeout": 5.0,
    }

    async def run_master():
        return await master_app.ainvoke(master_input)

    master_task = asyncio.create_task(run_master())

    # Wait dynamically for HITL suspension
    target_session = f"hitl_b1_ep3_iter1"
    for _ in range(50):
        pending = hitl_manager.get_pending()
        if any(p["session_id"] == target_session for p in pending):
            break
        await asyncio.sleep(0.05)

    pending = hitl_manager.get_pending()
    assert any(p["session_id"] == target_session for p in pending)

    # Resume HITL with author feedback and overrides
    overridden_draft = (
        "【第3話：魔王軍同盟の夜明け】"
        "主人公と魔王軍の使者は互いの思惑を腹に収め、血の契りを交わした。"
        "かつての敵と背中を預け合う奇妙な連帯感が、新たな運命の歯車を狂わせていく。"
    ) * 15

    resumed = await hitl_manager.resume(
        session_id=target_session,
        response_data={
            "session_id": target_session,
            "approved": True,
            "feedback": "Dramatic tone confirmed",
            "overrides": {
                "draft_content": overridden_draft,
            },
        },
    )
    assert resumed is True

    # Wait for MasterGraph to finish
    final_master_state = await master_task

    assert final_master_state is not None
    writing_results = final_master_state.get("writing_results", {})
    assert 3 in writing_results
    assert "魔王軍同盟の夜明け" in writing_results[3]["draft_content"]
    assert writing_results[3]["branch_id"] == 201
    assert writing_results[3]["hitl_status"] == "resumed"

    # Verify complete event chain
    assert any(ev[0] == "HITL_SUSPENDED" for ev in events_log)
    assert any(ev[0] == "HITL_RESUMED" for ev in events_log)
