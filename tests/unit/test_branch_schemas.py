"""
tests/unit/test_branch_schemas.py - Branch and HITL schemas & model validation
"""

import pytest
from src.backend.database.models import Branch
from src.schemas.ux_schemas import (
    BranchCreateRequest,
    BranchCreateResponse,
    HITLRequestPayload,
    HITLResumePayload,
    WhatIfResponse,
)
from src.backend.workflows.state import WritingGraphState, MasterGraphState


def test_branch_model_attributes():
    branch = Branch(
        id=2,
        book_id=1,
        name="What-If Stealth Route",
        parent_id=1,
        fork_ep_num=3,
        divergence_reason="Stealth approach: Avoid direct confrontation and steal secret documents",
    )
    assert branch.book_id == 1
    assert branch.name == "What-If Stealth Route"
    assert branch.parent_id == 1
    assert branch.fork_ep_num == 3
    assert "Stealth" in branch.divergence_reason


def test_branch_schemas():
    req = BranchCreateRequest(
        book_id=1,
        parent_branch_id=1,
        fork_ep_num=3,
        new_name="Stealth Route",
        divergence_reason="Chose stealth over fight",
        what_if_snippet="MC sneaks through the alley...",
    )
    assert req.book_id == 1
    assert req.fork_ep_num == 3
    assert req.new_name == "Stealth Route"

    res = BranchCreateResponse(
        branch_id=2,
        book_id=1,
        name=req.new_name,
        parent_id=req.parent_branch_id,
        fork_ep_num=req.fork_ep_num,
        divergence_reason=req.divergence_reason,
    )
    assert res.branch_id == 2
    assert res.status == "created"


def test_hitl_schemas():
    hitl_req = HITLRequestPayload(
        session_id="sess-12345",
        task_id="task-001",
        step_name="generate_draft",
        prompt_preview="Please write episode 3...",
        current_content="Initial draft text...",
        parameters={"passion": 0.8},
        options=["approve", "reject", "edit"],
        timeout_seconds=300,
    )
    assert hitl_req.session_id == "sess-12345"
    assert hitl_req.timeout_seconds == 300

    hitl_res = HITLResumePayload(
        session_id="sess-12345",
        approved=True,
        feedback="Looks good, just made a small tweak",
        overrides={"draft_content": "Modified draft text..."},
    )
    assert hitl_res.approved is True
    assert "draft_content" in hitl_res.overrides


def test_state_typed_dicts():
    writing_state: WritingGraphState = {
        "book_id": 1,
        "branch_id": 2,
        "ep_num": 3,
        "hitl_status": "waiting",
        "hitl_override_data": {"test_key": "test_val"},
    }
    assert writing_state["hitl_status"] == "waiting"

    master_state: MasterGraphState = {
        "task_id": "master-1",
        "active_branch_id": 2,
    }
    assert master_state["active_branch_id"] == 2
