from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

import src.backend.routers.branches as branches_module
from src.backend.routers.branches import (
    get_branch_stats,
    get_branch_choice_stats,
    play_load,
    play_end,
    get_playthrough,
    list_branch_nodes,
    create_branch_node,
    delete_branch_node,
    validate_branch_graph,
)
from src.backend.schemas.branch_play import (
    BranchPlayEndRequest,
    BranchPlayStateResponse,
    BranchPlayPlaythroughResponse,
    BranchPlaySessionResponse,
)
from src.backend.schemas.branch import BranchResponse


def make_branch(branch_id=1, book_id=10, name="Branch A", parent_id=None,
               fork_ep_num=0):
    return MagicMock(id=branch_id, book_id=book_id, name=name,
                     parent_id=parent_id, fork_ep_num=fork_ep_num,
                     created_at=datetime.now())


def make_session():
    session = MagicMock()
    session.commit = AsyncMock()
    return session


def patch_branch_repo(monkeypatch, repo, chapter_repo=None):
    """BranchRepository / ChapterRepository を両モジュールにパッチする。

    branches.py は src.backend.database.repositories.branch を import するが、
    実体は src.infrastructure.repositories.branch から re-export されるため
    両方を差し替える必要がある。
    """
    monkeypatch.setattr(branches_module, "BranchRepository", lambda s: repo)
    import src.backend.database.repositories.branch as backend_branch
    import src.infrastructure.repositories.branch as infra_branch
    monkeypatch.setattr(backend_branch, "BranchRepository", lambda s: repo)
    monkeypatch.setattr(infra_branch, "BranchRepository", lambda s: repo)
    if chapter_repo is not None:
        monkeypatch.setattr(branches_module, "ChapterRepository", lambda s: chapter_repo)
        import src.backend.database.repositories.chapter as backend_chapter
        import src.infrastructure.repositories.chapter as infra_chapter
        monkeypatch.setattr(backend_chapter, "ChapterRepository", lambda s: chapter_repo)
        monkeypatch.setattr(infra_chapter, "ChapterRepository", lambda s: chapter_repo)
    return repo


# ============================================================================
# get_branch_stats
# ============================================================================

@pytest.mark.asyncio
async def test_get_branch_stats():
    session = make_session()
    repo = MagicMock()
    repo.get_branch_tree = AsyncMock(return_value=[
        make_branch(1, book_id=10, name="Main"),
        make_branch(2, book_id=10, name="IF Branch"),
    ])
    repo.list_play_sessions = AsyncMock(return_value=[
        MagicMock(
            branch_id=1, book_id=10, current_node_id="n1",
            context_json={"history": [{"to": "n2"}, {"to": "n3"}]},
            save_points_json=[1, 2, 3], status="completed", updated_at=datetime.now()
        ),
        MagicMock(
            branch_id=2, book_id=10, current_node_id="n1",
            context_json={"history": [{"to": "n2"}]},
            save_points_json=[], status="active", updated_at=datetime.now()
        ),
        MagicMock(
            branch_id=1, book_id=10, current_node_id="n1",
            context_json={"history": []},
            save_points_json=[], status="abandoned", updated_at=datetime.now()
        ),
    ])

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await get_branch_stats(10, session=session)

    assert result["book_id"] == 10
    assert result["branch_count"] == 2
    assert result["session_total"] == 3
    assert result["session_completed"] == 1
    assert result["session_abandoned"] == 1
    assert result["session_active"] == 1
    assert result["total_choices"] == 3
    assert result["unique_paths"] == 3


# ============================================================================
# get_branch_choice_stats
# ============================================================================

@pytest.mark.asyncio
async def test_get_branch_choice_stats():
    session = make_session()
    repo = MagicMock()
    repo.list_play_sessions = AsyncMock(return_value=[
        MagicMock(
            branch_id=1, book_id=10, current_node_id="n1",
            context_json={"history": [
                {"choice_id": "c1", "to": "n2"},
                {"choice_id": "c2", "to": "n3"},
                {"choice_id": "c1", "to": "n4"},
            ]},
            save_points_json=[], status="active", updated_at=datetime.now()
        ),
        MagicMock(
            branch_id=2, book_id=10, current_node_id="n1",
            context_json={"history": [
                {"choice_id": "c2", "to": "n2"},
            ]},
            save_points_json=[], status="active", updated_at=datetime.now()
        ),
    ])

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await get_branch_choice_stats(10, session=session)

    assert result["book_id"] == 10
    assert result["choice_counts"]["c1"] == 2
    assert result["choice_counts"]["c2"] == 2
    assert result["total_choices"] == 4


# ============================================================================
# play_load
# ============================================================================

@pytest.mark.asyncio
async def test_play_load():
    session = make_session()
    session_id = str(uuid.uuid4())
    repo = MagicMock()
    repo.get_play_session = AsyncMock(return_value=MagicMock(
        branch_id=1, book_id=10, current_node_id="n1",
        context_json={"key": "value"},
        save_points_json=[
            {"node_id": "n1", "context": {"key": "value"}, "saved_at": "2026-01-01T00:00:00"},
            {"node_id": "n2", "context": {"other": "data"}, "saved_at": "2026-01-02T00:00:00"},
        ],
        status="active", updated_at=datetime.now()
    ))
    repo.update_play_session_state = AsyncMock()

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with patch("src.backend.routers.branches.get_play_state", new_callable=AsyncMock) as mock_get_play_state:
            mock_get_play_state.return_value = BranchPlayStateResponse(
                session_id=session_id,
                book_id=10,
                branch_id=1,
                current_node_id="n2",
                context={"other": "data"},
                available_choices=[],
                save_points_count=2,
                status="active",
                updated_at=datetime.now()
            )
            result = await play_load(session_id, index=1, session=session)

    assert result.current_node_id == "n2"
    assert result.context == {"other": "data"}
    repo.update_play_session_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_play_load_invalid_index():
    session = make_session()
    session_id = str(uuid.uuid4())
    repo = MagicMock()
    repo.get_play_session = AsyncMock(return_value=MagicMock(
        branch_id=1, book_id=10, current_node_id="n1",
        context_json={"key": "value"},
        save_points_json=[{"node_id": "n1", "context": {"key": "value"}, "saved_at": "2026-01-01T00:00:00"}],
        status="active", updated_at=datetime.now()
    ))

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc_info:
            await play_load(session_id, index=5, session=session)
        assert exc_info.value.status_code == 400
        assert "Save index out of range" in exc_info.value.detail


# ============================================================================
# play_end
# ============================================================================

@pytest.mark.asyncio
async def test_play_end():
    session = make_session()
    session_id = str(uuid.uuid4())
    payload = BranchPlayEndRequest(status="completed")
    repo = MagicMock()
    repo.end_play_session = AsyncMock()
    repo.get_play_session = AsyncMock(return_value=MagicMock(
        branch_id=1, book_id=10, current_node_id="n1",
        status="active", updated_at=datetime.now()
    ))

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await play_end(session_id, payload=payload, session=session)

    assert result.status == "completed"
    repo.end_play_session.assert_awaited_once_with(session_id, status="completed")


# ============================================================================
# get_playthrough
# ============================================================================

@pytest.mark.asyncio
async def test_get_playthrough():
    session = make_session()
    session_id = str(uuid.uuid4())
    repo = MagicMock()
    repo.get_play_session = AsyncMock(return_value=MagicMock(
        branch_id=1, book_id=10, current_node_id="n1",
        context_json={
            "history": [{"from": "n1", "choice_id": "c1", "to": "n2"}],
            "flags": {"flag1": True},
            "variables": {"var1": "value"},
            "ending": "good_ending"
        },
        status="active", updated_at=datetime.now()
    ))

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await get_playthrough(session_id, session=session)

    assert result.session_id == session_id
    assert result.book_id == 10
    assert result.branch_id == 1
    assert result.history == [{"from": "n1", "choice_id": "c1", "to": "n2"}]
    assert result.flags == {"flag1": True}
    assert result.variables == {"var1": "value"}
    assert result.final_ending == "good_ending"


# ============================================================================
# list_branch_nodes
# ============================================================================

@pytest.mark.asyncio
async def test_list_branch_nodes():
    session = make_session()
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value={
        "entry_node_id": "node1",
        "nodes": {
            "node1": {"id": "node1", "content": "Node 1"},
            "node2": {"id": "node2", "content": "Node 2"},
        }
    })

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await list_branch_nodes(10, 1, session=session)

    assert result["branch_id"] == 1
    assert result["entry_node_id"] == "node1"
    assert len(result["nodes"]) == 2
    assert "node1" in result["nodes"]
    assert "node2" in result["nodes"]


# ============================================================================
# create_branch_node
# ============================================================================

@pytest.mark.asyncio
async def test_create_branch_node():
    session = make_session()
    node_data = {"id": "node3", "content": "New node"}
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value={
        "nodes": {
            "node1": {"id": "node1"},
            "node2": {"id": "node2"}
        },
        "entry_node_id": "node1"
    })
    repo.save_branch_graph = AsyncMock()

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await create_branch_node(10, 1, node_data, session=session)

    assert result["branch_id"] == 1
    assert result["node"] == node_data
    repo.save_branch_graph.assert_awaited_once()


# ============================================================================
# delete_branch_node
# ============================================================================

@pytest.mark.asyncio
async def test_delete_branch_node():
    session = make_session()
    node_id = "node2"
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value={
        "nodes": {
            "node1": {"id": "node1", "choices": []},
            "node2": {"id": "node2", "choices": []}
        },
        "entry_node_id": "node1"
    })
    repo.save_branch_graph = AsyncMock()

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await delete_branch_node(10, 1, node_id, session=session)

    assert result["branch_id"] == 1
    assert result["deleted"] == node_id
    repo.save_branch_graph.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_branch_node_referenced():
    session = make_session()
    node_id = "node2"
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value={
        "nodes": {
            "node1": {"id": "node1", "choices": [{"target_node_id": "node2"}]},
            "node2": {"id": "node2", "choices": []}
        },
        "entry_node_id": "node1"
    })

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc_info:
            await delete_branch_node(10, 1, node_id, session=session)
        assert exc_info.value.status_code == 422
        assert "referenced by" in exc_info.value.detail


# ============================================================================
# validate_branch_graph
# ============================================================================

@pytest.mark.asyncio
async def test_validate_branch_graph():
    session = make_session()
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value={
        "entry_node_id": "node1",
        "nodes": {
            "node1": {"id": "node1", "choices": [{"target_node_id": "node2"}]},
            "node2": {"id": "node2", "choices": []}
        }
    })

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await validate_branch_graph(10, 1, session=session)

    assert result["branch_id"] == 1
    assert result["valid"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_validate_branch_graph_invalid_entry():
    session = make_session()
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value={
        "entry_node_id": "",  # empty entry node
        "nodes": {
            "node1": {"id": "node1", "choices": []}
        }
    })

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await validate_branch_graph(10, 1, session=session)

    assert result["branch_id"] == 1
    assert result["valid"] is False
    assert "entry_node_id is empty" in result["errors"]