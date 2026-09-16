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
    get_branch_diff,
    get_branch_graph,
    fork_branch,
    merge_branches,
    preview_merge,
    save_branch_graph,
    start_play_session,
    get_play_state,
    play_choose,
    play_save,
    play_load,
    play_end,
    get_playthrough,
    list_branch_nodes,
    create_branch_node,
    delete_branch_node,
    validate_branch_graph,
)
from src.backend.schemas.branch import (
    BranchForkRequest,
    BranchMergeRequest,
    BranchResponse,
)
from src.backend.schemas.branch_play import (
    BranchPlayChooseRequest,
    BranchPlayEndRequest,
    BranchPlayRequest,
    BranchPlayStateResponse,
)
from src.domain.models.branch import BranchDbModelCreate


# ==============================================================================
# Helper Functions (already tested in test_router_branches.py, but we keep for completeness)
# ==============================================================================

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


# ==============================================================================
# Branch Endpoints Tests
# ==============================================================================

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


@pytest.mark.asyncio
async def test_get_branch_diff():
    mock_session = AsyncMock()
    mock_chapter_a = MagicMock()
    mock_chapter_a.content = "Original content"
    mock_chapter_b = MagicMock()
    mock_chapter_b.content = "Modified content"
    mock_branch_a = MagicMock()
    mock_branch_a.name = "Branch A"
    mock_branch_b = MagicMock()
    mock_branch_b.name = "Branch B"

    with patch("src.backend.routers.branches.BranchRepository") as MockBranchRepo, \
         patch("src.backend.routers.branches.ChapterRepository") as MockChapterRepo:

        branch_repo_inst = MockBranchRepo.return_value
        chapter_repo_inst = MockChapterRepo.return_value

        branch_repo_inst.get_branch = AsyncMock(side_effect=[mock_branch_a, mock_branch_b])
        chapter_repo_inst.get_chapter = AsyncMock(side_effect=[mock_chapter_a, mock_chapter_b])

        res = await get_branch_diff(
            book_id=1,
            branchA=1,
            branchB=2,
            chapter=1,
            session=mock_session
        )

        assert res["chapter_number"] == 1
        assert res["branch_a_name"] == "Branch A"
        assert res["branch_b_name"] == "Branch B"
        assert res["content_a"] == "Original content"
        assert res["content_b"] == "Modified content"
        assert "-Original content" in res["diff_unified"] or "+Modified content" in res["diff_unified"]


@pytest.mark.asyncio
async def test_get_branch_graph():
    mock_session = AsyncMock()
    mock_graph = {"nodes": {"node1": {"id": "node1"}}}

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)

        res = await get_branch_graph(
            book_id=1,
            branch_id=1,
            session=mock_session
        )

        assert res.branch_id == 1
        assert res.graph == mock_graph


@pytest.mark.asyncio
async def test_get_branch_graph_not_found():
    mock_session = AsyncMock()

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_branch_graph(
                book_id=1,
                branch_id=1,
                session=mock_session
            )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_fork_branch():
    mock_session = AsyncMock()
    payload = BranchForkRequest(
        book_id=1,
        name="Forked Branch",
        parent_id=10,
        fork_ep_num=5,
    )

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.create_branch = AsyncMock(return_value=2)
        mock_branch = MagicMock()
        mock_branch.id = 2
        mock_branch.book_id = 1
        mock_branch.name = "Forked Branch"
        mock_branch.parent_id = 10
        mock_branch.fork_ep_num = 5
        mock_branch.created_at = datetime.now()
        repo_inst.get_branch = AsyncMock(return_value=mock_branch)

        res = await fork_branch(
            book_id=1,
            payload=payload,
            session=mock_session
        )

        assert res.id == 2
        assert res.name == "Forked Branch"
        repo_inst.create_branch.assert_awaited_once()


@pytest.mark.asyncio
async def test_merge_branches():
    mock_session = AsyncMock()
    payload = BranchMergeRequest(
        source_branch_id=11,
        target_branch_id=10,
        merge_ep_num=5,
    )
    mock_target_graph = {"nodes": {}}

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_target_graph)
        repo_inst.save_branch_graph = AsyncMock()
        mock_branch = MagicMock()
        mock_branch.id = 10
        mock_branch.book_id = 1
        mock_branch.name = "Target Branch"
        mock_branch.parent_id = None
        mock_branch.fork_ep_num = 0
        mock_branch.created_at = datetime.now()
        repo_inst.get_branch = AsyncMock(return_value=mock_branch)

        res = await merge_branches(
            book_id=1,
            payload=payload,
            session=mock_session
        )

        assert res.id == 10
        assert res.name == "Target Branch"
        assert repo_inst.load_branch_graph.call_count == 1  # load only (save is separate)
        repo_inst.save_branch_graph.assert_awaited_once()


@pytest.mark.asyncio
async def test_preview_merge_no_conflict():
    mock_session = AsyncMock()
    payload = BranchMergeRequest(
        source_branch_id=11,
        target_branch_id=10,
        merge_ep_num=5,
    )
    mock_source_branch = MagicMock()
    mock_source_branch.id = 11
    mock_source_branch.name = "Source"
    mock_target_branch = MagicMock()
    mock_target_branch.id = 10
    mock_target_branch.name = "Target"
    mock_target_branch.parent_id = None
    mock_source_chapter = MagicMock()
    mock_source_chapter.content = "Same content"
    mock_target_chapter = MagicMock()
    mock_target_chapter.content = "Same content"

    with patch("src.backend.routers.branches.BranchRepository") as MockBranchRepo, \
         patch("src.backend.routers.branches.ChapterRepository") as MockChapterRepo:

        branch_repo_inst = MockBranchRepo.return_value
        chapter_repo_inst = MockChapterRepo.return_value

        branch_repo_inst.get_branch = AsyncMock(side_effect=[mock_source_branch, mock_target_branch])
        chapter_repo_inst.get_chapter = AsyncMock(side_effect=[mock_source_chapter, mock_target_chapter])

        res = await preview_merge(
            book_id=1,
            payload=payload,
            session=mock_session
        )

        assert res["can_merge"] is True
        assert res["has_conflict"] is False
        assert res["merged_content"] == "Same content"


@pytest.mark.asyncio
async def test_preview_merge_with_conflict():
    mock_session = AsyncMock()
    payload = BranchMergeRequest(
        source_branch_id=11,
        target_branch_id=10,
        merge_ep_num=5,
    )
    mock_source_branch = MagicMock()
    mock_source_branch.id = 11
    mock_source_branch.name = "Source"
    mock_target_branch = MagicMock()
    mock_target_branch.id = 10
    mock_target_branch.name = "Target"
    mock_target_branch.parent_id = None
    mock_source_chapter = MagicMock()
    mock_source_chapter.content = "Source content"
    mock_target_chapter = MagicMock()
    mock_target_chapter.content = "Target content"

    with patch("src.backend.routers.branches.BranchRepository") as MockBranchRepo, \
         patch("src.backend.routers.branches.ChapterRepository") as MockChapterRepo:

        branch_repo_inst = MockBranchRepo.return_value
        chapter_repo_inst = MockChapterRepo.return_value

        branch_repo_inst.get_branch = AsyncMock(side_effect=[mock_source_branch, mock_target_branch])
        chapter_repo_inst.get_chapter = AsyncMock(side_effect=[mock_source_chapter, mock_target_chapter])

        res = await preview_merge(
            book_id=1,
            payload=payload,
            session=mock_session
        )

        assert res["can_merge"] is False
        assert res["has_conflict"] is True
        assert len(res["conflict_chunks"]) == 1
        assert res["conflict_chunks"][0]["source"] == "Source content"
        assert res["conflict_chunks"][0]["target"] == "Target content"


@pytest.mark.asyncio
async def test_save_branch_graph():
    mock_session = AsyncMock()
    graph_data = {"nodes": {"node1": {"id": "node1"}}}

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.save_branch_graph = AsyncMock()
        mock_branch = MagicMock()
        mock_branch.id = 1
        mock_branch.book_id = 1
        repo_inst.get_branch = AsyncMock(return_value=mock_branch)

        res = await save_branch_graph(
            book_id=1,
            branch_id=1,
            graph=graph_data,
            session=mock_session
        )

        assert res.branch_id == 1
        assert res.graph == graph_data
        repo_inst.save_branch_graph.assert_awaited_once_with(1, graph_data)


@pytest.mark.asyncio
async def test_save_branch_graph_not_found():
    mock_session = AsyncMock()
    graph_data = {"nodes": {"node1": {"id": "node1"}}}

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_branch = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await save_branch_graph(
                book_id=1,
                branch_id=1,
                graph=graph_data,
                session=mock_session
            )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_start_play_session():
    mock_session = AsyncMock()
    payload = BranchPlayRequest(
        book_id=1,
        branch_id=10,
    )
    mock_branch = MagicMock()
    mock_branch.id = 10
    mock_branch.book_id = 1
    mock_graph = {"entry_node_id": "node1"}

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_branch = AsyncMock(return_value=mock_branch)
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)
        repo_inst.create_play_session = AsyncMock()

        res = await start_play_session(
            payload=payload,
            session=mock_session
        )

        assert res.book_id == 1
        assert res.branch_id == 10
        assert res.status == "active"
        repo_inst.create_play_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_play_state():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.current_node_id = "node1"
    mock_sess.context_json = {"key": "value"}
    mock_sess.save_points_json = []
    mock_sess.status = "active"
    mock_sess.updated_at = datetime.now()
    mock_graph = {"nodes": {"node1": {"choices": []}}}

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)

        res = await get_play_state(
            session_id=session_id,
            session=mock_session
        )

        assert res.session_id == session_id
        assert res.book_id == 1
        assert res.branch_id == 10
        assert res.current_node_id == "node1"
        assert res.context == {"key": "value"}
        assert res.status == "active"


@pytest.mark.asyncio
async def test_get_play_state_invalid_uuid():
    mock_session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_play_state(
            session_id="invalid-uuid",
            session=mock_session
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_play_choose():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    payload = BranchPlayChooseRequest(
        session_id=session_id,
        choice_id="choice-a",
    )
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.current_node_id = "node1"
    mock_sess.version = 1
    mock_sess.context_json = {}
    mock_sess.save_points_json = []
    mock_sess.status = "active"
    mock_graph = {
        "nodes": {
            "node1": {
                "choices": [
                    {"id": "choice-a", "target_node_id": "node2", "effects": {}}
                ]
            }
        }
    }
    mock_updated_sess = MagicMock()
    mock_updated_sess.id = session_id
    mock_updated_sess.book_id = 1
    mock_updated_sess.branch_id = 10
    mock_updated_sess.current_node_id = "node2"
    mock_updated_sess.context_json = {}
    mock_updated_sess.save_points_json = []
    mock_updated_sess.status = "active"
    mock_updated_sess.updated_at = datetime.now()

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)
        repo_inst.update_play_session_state_optimistic = AsyncMock(return_value=True)
        repo_inst.get_play_session = AsyncMock(side_effect=[mock_sess, mock_updated_sess])

        res = await play_choose(
            session_id=session_id,
            payload=payload,
            session=mock_session
        )

        assert res.current_node_id == "node2"


@pytest.mark.asyncio
async def test_play_choose_invalid_choice():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    payload = BranchPlayChooseRequest(
        session_id=session_id,
        choice_id="invalid-choice",
    )
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.current_node_id = "node1"
    mock_sess.version = 1
    mock_sess.context_json = {}
    mock_sess.save_points_json = []
    mock_sess.status = "active"
    mock_graph = {
        "nodes": {
            "node1": {
                "choices": [
                    {"id": "choice-a", "target_node_id": "node2", "effects": {}}
                ]
            }
        }
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)

        with pytest.raises(HTTPException) as exc_info:
            await play_choose(
                session_id=session_id,
                payload=payload,
                session=mock_session
            )
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_play_save():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.current_node_id = "node1"
    mock_sess.context_json = {"key": "value"}
    mock_sess.save_points_json = []
    mock_sess.status = "active"
    mock_updated_sess = MagicMock()
    mock_updated_sess.id = session_id
    mock_updated_sess.book_id = 1
    mock_updated_sess.branch_id = 10
    mock_updated_sess.current_node_id = "node1"
    mock_updated_sess.context_json = {"key": "value"}
    mock_updated_sess.save_points_json = [{"node_id": "node1", "context": {"key": "value"}, "saved_at": datetime.now().isoformat()}]
    mock_updated_sess.status = "active"
    mock_updated_sess.updated_at = datetime.now()

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)
        repo_inst.update_play_session_state = AsyncMock()
        # Mock get_play_state function that is called internally
        with patch("src.backend.routers.branches.get_play_state", new_callable=AsyncMock) as mock_get_play_state:
            mock_get_play_state.return_value = BranchPlayStateResponse(
                session_id=session_id,
                book_id=1,
                branch_id=10,
                current_node_id="node1",
                context={"key": "value"},
                available_choices=[],
                save_points_count=1,
                status="active",
                updated_at=datetime.now()
            )

            res = await play_save(
                session_id=session_id,
                session=mock_session
            )

            assert res.save_points_count == 1


@pytest.mark.asyncio
async def test_play_load():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.current_node_id = "node1"
    mock_sess.context_json = {"key": "value"}
    mock_sess.save_points_json = [
        {"node_id": "node1", "context": {"key": "value"}, "saved_at": datetime.now().isoformat()},
        {"node_id": "node2", "context": {"other": "data"}, "saved_at": datetime.now().isoformat()}
    ]
    mock_updated_sess = MagicMock()
    mock_updated_sess.id = session_id
    mock_updated_sess.book_id = 1
    mock_updated_sess.branch_id = 10
    mock_updated_sess.current_node_id = "node2"
    mock_updated_sess.context_json = {"other": "data"}
    mock_updated_sess.save_points_json = [
        {"node_id": "node1", "context": {"key": "value"}, "saved_at": datetime.now().isoformat()},
        {"node_id": "node2", "context": {"other": "data"}, "saved_at": datetime.now().isoformat()}
    ]
    mock_updated_sess.status = "active"
    mock_updated_sess.updated_at = datetime.now()

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)
        repo_inst.update_play_session_state = AsyncMock()
        # Mock get_play_state function that is called internally
        with patch("src.backend.routers.branches.get_play_state", new_callable=AsyncMock) as mock_get_play_state:
            mock_get_play_state.return_value = BranchPlayStateResponse(
                session_id=session_id,
                book_id=1,
                branch_id=10,
                current_node_id="node2",
                context={"other": "data"},
                available_choices=[],
                save_points_count=2,
                status="active",
                updated_at=datetime.now()
            )

            res = await play_load(
                session_id=session_id,
                index=1,
                session=mock_session
            )

            assert res.current_node_id == "node2"
            assert res.context == {"other": "data"}


@pytest.mark.asyncio
async def test_play_load_invalid_index():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.current_node_id = "node1"
    mock_sess.context_json = {"key": "value"}
    mock_sess.save_points_json = [{"node_id": "node1", "context": {"key": "value"}, "saved_at": datetime.now().isoformat()}]
    mock_sess.status = "active"

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)

        with pytest.raises(HTTPException) as exc_info:
            await play_load(
                session_id=session_id,
                index=5,  # out of range
                session=mock_session
            )
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_play_end():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    payload = BranchPlayEndRequest(status="completed")
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.current_node_id = "node1"
    mock_sess.status = "active"

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.end_play_session = AsyncMock()
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)

        res = await play_end(
            session_id=session_id,
            payload=payload,
            session=mock_session
        )

        assert res.status == "completed"
        repo_inst.end_play_session.assert_awaited_once_with(session_id, status="completed")


@pytest.mark.asyncio
async def test_get_playthrough():
    mock_session = AsyncMock()
    session_id = str(uuid.uuid4())
    mock_sess = MagicMock()
    mock_sess.id = session_id
    mock_sess.book_id = 1
    mock_sess.branch_id = 10
    mock_sess.context_json = {
        "history": [{"from": "node1", "choice_id": "choice-a", "to": "node2"}],
        "flags": {"flag1": True},
        "variables": {"var1": "value"},
        "ending": "good_ending"
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.get_play_session = AsyncMock(return_value=mock_sess)

        res = await get_playthrough(
            session_id=session_id,
            session=mock_session
        )

        assert res.session_id == session_id
        assert res.book_id == 1
        assert res.branch_id == 10
        assert res.history == [{"from": "node1", "choice_id": "choice-a", "to": "node2"}]
        assert res.flags == {"flag1": True}
        assert res.variables == {"var1": "value"}
        assert res.final_ending == "good_ending"


@pytest.mark.asyncio
async def test_list_branch_nodes():
    mock_session = AsyncMock()
    mock_graph = {
        "entry_node_id": "node1",
        "nodes": {
            "node1": {"id": "node1"},
            "node2": {"id": "node2"}
        }
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)

        res = await list_branch_nodes(
            book_id=1,
            branch_id=1,
            session=mock_session
        )

        assert res["branch_id"] == 1
        assert res["entry_node_id"] == "node1"
        assert len(res["nodes"]) == 2
        assert "node1" in res["nodes"]
        assert "node2" in res["nodes"]


@pytest.mark.asyncio
async def test_create_branch_node():
    mock_session = AsyncMock()
    node_data = {"id": "node3", "content": "New node"}
    mock_graph = {
        "nodes": {
            "node1": {"id": "node1"},
            "node2": {"id": "node2"}
        },
        "entry_node_id": "node1"
    }
    mock_updated_graph = {
        "nodes": {
            "node1": {"id": "node1"},
            "node2": {"id": "node2"},
            "node3": {"id": "node3", "content": "New node"}
        },
        "entry_node_id": "node1"
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)
        repo_inst.save_branch_graph = AsyncMock()

        res = await create_branch_node(
            book_id=1,
            branch_id=1,
            node=node_data,
            session=mock_session
        )

        assert res["branch_id"] == 1
        assert res["node"] == node_data
        repo_inst.save_branch_graph.assert_awaited_once_with(1, mock_updated_graph)


@pytest.mark.asyncio
async def test_delete_branch_node():
    mock_session = AsyncMock()
    node_id = "node2"
    mock_graph = {
        "nodes": {
            "node1": {"id": "node1", "choices": []},
            "node2": {"id": "node2", "choices": []}
        },
        "entry_node_id": "node1"
    }
    mock_updated_graph = {
        "nodes": {
            "node1": {"id": "node1", "choices": []}
        },
        "entry_node_id": "node1"
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)
        repo_inst.save_branch_graph = AsyncMock()

        res = await delete_branch_node(
            book_id=1,
            branch_id=1,
            node_id=node_id,
            session=mock_session
        )

        assert res["branch_id"] == 1
        assert res["deleted"] == node_id
        repo_inst.save_branch_graph.assert_awaited_once_with(1, mock_updated_graph)


@pytest.mark.asyncio
async def test_delete_branch_node_referenced():
    mock_session = AsyncMock()
    node_id = "node2"
    mock_graph = {
        "nodes": {
            "node1": {"id": "node1", "choices": [{"target_node_id": "node2"}]},
            "node2": {"id": "node2", "choices": []}
        },
        "entry_node_id": "node1"
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)

        with pytest.raises(HTTPException) as exc_info:
            await delete_branch_node(
                book_id=1,
                branch_id=1,
                node_id=node_id,
                session=mock_session
            )
        assert exc_info.value.status_code == 422
        assert "referenced by" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_branch_graph():
    mock_session = AsyncMock()
    mock_graph = {
        "entry_node_id": "node1",
        "nodes": {
            "node1": {"id": "node1", "choices": [{"target_node_id": "node2"}]},
            "node2": {"id": "node2", "choices": []}
        }
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)

        res = await validate_branch_graph(
            book_id=1,
            branch_id=1,
            session=mock_session
        )

        assert res["branch_id"] == 1
        assert res["valid"] is True
        assert res["errors"] == []


@pytest.mark.asyncio
async def test_validate_branch_graph_invalid_entry():
    mock_session = AsyncMock()
    mock_graph = {
        "entry_node_id": "",  # empty entry node
        "nodes": {
            "node1": {"id": "node1", "choices": []}
        }
    }

    with patch("src.backend.routers.branches.BranchRepository") as MockRepo:
        repo_inst = MockRepo.return_value
        repo_inst.load_branch_graph = AsyncMock(return_value=mock_graph)

        res = await validate_branch_graph(
            book_id=1,
            branch_id=1,
            session=mock_session
        )

        assert res["branch_id"] == 1
        assert res["valid"] is False
        assert "entry_node_id is empty" in res["errors"]


# WebSocket test is more complex and might require a different approach.
# We'll skip it for now to keep the test suite focused and manageable.
# If needed, we can add a separate test for WebSocket using pytest-asyncio and mocking WebSocket.
