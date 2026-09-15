from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from src.backend.routers.branches import (
    _to_response,
    _validate_uuid,
    create_branch,
    get_branch_tree,
    list_branches,
)
from src.backend.schemas.branch import (
    BranchForkRequest,
    BranchMergeCommitRequest,
    BranchMergeRequest,
    BranchResponse,
)
from src.backend.schemas.branch_play import (
    BranchPlayChooseRequest,
    BranchPlayEndRequest,
    BranchPlayRequest,
)
from src.domain.models.branch import BranchDbModelCreate


def test_validate_uuid():
    valid = str(uuid.uuid4())
    assert _validate_uuid(valid) is True
    assert _validate_uuid("invalid-uuid") is False
    assert _validate_uuid("") is False


def test_to_response():
    mock_model = MagicMock()
    mock_model.id = 1
    mock_model.book_id = 100
    mock_model.name = "Root Branch"
    mock_model.parent_id = None
    mock_model.fork_ep_num = 0
    mock_model.created_at = datetime(2026, 1, 1, 12, 0, 0)

    res = _to_response(mock_model)
    assert isinstance(res, BranchResponse)
    assert res.id == 1
    assert res.book_id == 100
    assert res.name == "Root Branch"
    assert res.parent_id is None
    assert res.fork_ep_num == 0


def test_branch_schemas_validation():
    fork_req = BranchForkRequest(
        book_id=1,
        parent_id=10,
        fork_ep_num=3,
        name="IF ルート",
    )
    assert fork_req.book_id == 1
    assert fork_req.parent_id == 10
    assert fork_req.fork_ep_num == 3
    assert fork_req.name == "IF ルート"

    merge_req = BranchMergeRequest(
        source_branch_id=11,
        target_branch_id=10,
        merge_ep_num=5,
    )
    assert merge_req.source_branch_id == 11
    assert merge_req.merge_ep_num == 5

    from src.backend.schemas.branch import ResolvedChapterPayload
    commit_req = BranchMergeCommitRequest(
        source_branch_id=11,
        target_branch_id=10,
        merge_ep_num=5,
        resolved_chapters=[
            ResolvedChapterPayload(chapter_number=1, resolved_content="resolved text")
        ],
    )
    assert commit_req.source_branch_id == 11
    assert len(commit_req.resolved_chapters) == 1

    play_req = BranchPlayRequest(
        book_id=1,
        branch_id=10,
    )
    assert play_req.book_id == 1

    choose_req = BranchPlayChooseRequest(
        session_id=str(uuid.uuid4()),
        choice_id="choice-a",
    )
    assert choose_req.choice_id == "choice-a"


@pytest.mark.asyncio
async def test_create_branch_endpoint():
    payload = BranchDbModelCreate(
        book_id=1,
        name="New Branch",
        parent_id=None,
        fork_ep_num=0,
        graph_json={"nodes": []},
    )
    mock_session = AsyncMock()

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.create_branch = AsyncMock(return_value=1)
        repo_inst.save_branch_graph = AsyncMock()
        
        mock_branch = MagicMock()
        mock_branch.id = 1
        mock_branch.book_id = 1
        mock_branch.name = "New Branch"
        mock_branch.parent_id = None
        mock_branch.fork_ep_num = 0
        mock_branch.created_at = datetime.now()
        repo_inst.get_branch = AsyncMock(return_value=mock_branch)

        res = await create_branch(payload=payload, session=mock_session)
        assert res.id == 1
        assert res.name == "New Branch"
        repo_inst.create_branch.assert_awaited_once()
        repo_inst.save_branch_graph.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_branch_failed():
    payload = BranchDbModelCreate(
        book_id=1,
        name="Fail Branch",
        parent_id=None,
        fork_ep_num=0,
    )
    mock_session = AsyncMock()

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.create_branch = AsyncMock(return_value=2)
        repo_inst.get_branch = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await create_branch(payload=payload, session=mock_session)
        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_list_and_get_branch_tree():
    mock_user = MagicMock()
    mock_user.id = 42

    mock_b1 = MagicMock()
    mock_b1.id = 1
    mock_b1.book_id = 100
    mock_b1.name = "Main"
    mock_b1.parent_id = None
    mock_b1.fork_ep_num = 0
    mock_b1.created_at = datetime.now()

    mock_b2 = MagicMock()
    mock_b2.id = 2
    mock_b2.book_id = 100
    mock_b2.name = "IF Branch"
    mock_b2.parent_id = 1
    mock_b2.fork_ep_num = 3
    mock_b2.created_at = datetime.now()

    with patch("src.backend.routers.branches.UnitOfWork") as MockUoW, \
         patch("src.backend.routers.branches.verify_book_ownership", new_callable=AsyncMock), \
         patch("src.backend.routers.branches.BranchRepository") as MockRepo, \
         patch("src.backend.routers.branches.AppContainer.db"):
        
        uow_inst = MagicMock()
        uow_inst.__aenter__ = AsyncMock(return_value=uow_inst)
        uow_inst.__aexit__ = AsyncMock(return_value=None)
        MockUoW.return_value = uow_inst

        repo_inst = MockRepo.return_value
        repo_inst.get_branch_tree = AsyncMock(return_value=[mock_b1, mock_b2])

        # list_branches
        res_list = await list_branches(book_id=100, current_user=mock_user)
        assert len(res_list) == 2
        assert res_list[0].id == 1
        assert res_list[1].id == 2

        # get_branch_tree
        tree_data = await get_branch_tree(book_id=100, current_user=mock_user)
        assert "nodes" in tree_data
        assert "edges" in tree_data
        assert len(tree_data["nodes"]) == 2
        assert len(tree_data["edges"]) == 1
        assert tree_data["edges"][0]["source"] == 1
        assert tree_data["edges"][0]["target"] == 2
