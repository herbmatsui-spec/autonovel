"""Branches router coverage: diff, fork, merge, graph, play session flows."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

import src.backend.routers.branches as branches_module
from src.backend.routers.branches import (
    commit_branch_merge,
    fork_branch,
    get_branch_diff,
    get_branch_graph,
    get_play_state,
    merge_branches,
    preview_merge,
    save_branch_graph,
    start_play_session,
)


def make_branch(branch_id=1, book_id=10, name="Branch A", parent_id=None,
               fork_ep_num=0):
    return SimpleNamespace(id=branch_id, book_id=book_id, name=name,
                           parent_id=parent_id, fork_ep_num=fork_ep_num,
                           created_at=None)


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
# get_branch_diff
# ============================================================================


@pytest.mark.asyncio
async def test_get_branch_diff_success():
    session = make_session()
    branch_repo = MagicMock()
    branch_repo.get_branch = AsyncMock(
        side_effect=[make_branch(1, name="A"), make_branch(2, name="B")])
    chapter_repo = MagicMock()
    chapter_repo.get_chapter = AsyncMock(
        side_effect=[SimpleNamespace(content="line1\nline2"),
                     SimpleNamespace(content="line1\nline3")])

    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo, chapter_repo)
        result = await get_branch_diff(10, branchA=1, branchB=2, chapter=3,
                                       session=session)
    assert result["chapter_number"] == 3
    assert result["branch_a_name"] == "A"
    assert result["branch_b_name"] == "B"
    assert result["content_a"] == "line1\nline2"
    assert result["diff_unified"]
    assert result["diff_side_by_side"]


@pytest.mark.asyncio
async def test_get_branch_diff_branch_not_found():
    session = make_session()
    branch_repo = MagicMock()
    branch_repo.get_branch = AsyncMock(return_value=None)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo)
        with pytest.raises(HTTPException) as exc:
            await get_branch_diff(10, branchA=1, branchB=2, chapter=3, session=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_branch_diff_chapter_not_found_and_null_content():
    session = make_session()
    branch_repo = MagicMock()
    branch_repo.get_branch = AsyncMock(
        side_effect=[make_branch(1), make_branch(2)])
    chapter_repo = MagicMock()
    # First call: both None -> 404
    chapter_repo.get_chapter = AsyncMock(side_effect=[None, None])
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo, chapter_repo)
        with pytest.raises(HTTPException) as exc:
            await get_branch_diff(10, branchA=1, branchB=2, chapter=3, session=session)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Chapter not found"

    # Null content -> empty strings
    chapter_repo.get_chapter = AsyncMock(
        side_effect=[SimpleNamespace(content=None),
                     SimpleNamespace(content=None)])
    branch_repo.get_branch = AsyncMock(
        side_effect=[make_branch(1), make_branch(2)])
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo, chapter_repo)
        result = await get_branch_diff(10, branchA=1, branchB=2, chapter=3,
                                       session=session)
    assert result["content_a"] == ""
    assert result["content_b"] == ""
    # nameless branches -> default names
    chapter_repo.get_chapter = AsyncMock(
        side_effect=[SimpleNamespace(content="a"),
                     SimpleNamespace(content="a")])
    branch_repo.get_branch = AsyncMock(
        side_effect=[make_branch(1, name=None), make_branch(2, name=None)])
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo, chapter_repo)
        result2 = await get_branch_diff(10, branchA=1, branchB=2, chapter=3,
                                        session=session)
    assert result2["branch_a_name"] == "Branch 1"
    assert result2["branch_b_name"] == "Branch 2"


# ============================================================================
# get_branch_graph / save_branch_graph
# ============================================================================


@pytest.mark.asyncio
async def test_get_branch_graph_found_and_missing():
    session = make_session()
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value={"nodes": {}})
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await get_branch_graph(10, branch_id=1, session=session)
    assert result.branch_id == 1
    assert result.graph == {"nodes": {}}

    repo.load_branch_graph = AsyncMock(return_value=None)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc:
            await get_branch_graph(10, branch_id=999, session=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_save_branch_graph_found_and_missing():
    session = make_session()
    repo = MagicMock()
    repo.get_branch = AsyncMock(return_value=make_branch(1, book_id=10))
    repo.save_branch_graph = AsyncMock()
    graph = {"nodes": {"n1": {}}}
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await save_branch_graph(10, branch_id=1, graph=graph, session=session)
    assert result.graph == graph
    repo.save_branch_graph.assert_awaited_once_with(1, graph)
    session.commit.assert_awaited_once()

    # Wrong book
    repo.get_branch = AsyncMock(return_value=make_branch(1, book_id=99))
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc:
            await save_branch_graph(10, branch_id=1, graph=graph, session=session)
    assert exc.value.status_code == 404


# ============================================================================
# fork_branch
# ============================================================================


@pytest.mark.asyncio
async def test_fork_branch_success_and_failure():
    session = make_session()
    repo = MagicMock()
    repo.create_branch = AsyncMock(return_value=5)
    repo.get_branch = AsyncMock(return_value=make_branch(5, name="Fork"))
    payload = SimpleNamespace(name="Fork", parent_id=1, fork_ep_num=2)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await fork_branch(10, payload, session=session)
    assert result.id == 5
    assert result.name == "Fork"
    session.commit.assert_awaited_once()

    # Fork failed
    repo.get_branch = AsyncMock(return_value=None)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc:
            await fork_branch(10, payload, session=session)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Fork failed"


# ============================================================================
# merge_branches
# ============================================================================


@pytest.mark.asyncio
async def test_merge_branches_success():
    session = make_session()
    repo = MagicMock()
    target_graph = {"nodes": {"existing": {}}}
    repo.load_branch_graph = AsyncMock(return_value=target_graph)
    repo.save_branch_graph = AsyncMock()
    repo.get_branch = AsyncMock(return_value=make_branch(2, name="Target"))
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2, merge_ep_num=5)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await merge_branches(10, payload, session=session)
    assert result.id == 2
    # merge node added
    assert "merge_ep5" in target_graph["nodes"]
    node = target_graph["nodes"]["merge_ep5"]
    assert node["branch_type"] == "merge"
    assert node["parent_ids"] == [1, 2]
    repo.save_branch_graph.assert_awaited_once_with(2, target_graph)


@pytest.mark.asyncio
async def test_merge_branches_target_not_found_and_merge_failed():
    session = make_session()
    repo = MagicMock()
    repo.load_branch_graph = AsyncMock(return_value=None)
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2, merge_ep_num=5)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc:
            await merge_branches(10, payload, session=session)
    assert exc.value.status_code == 404

    # merge failed
    repo.load_branch_graph = AsyncMock(return_value={"nodes": {}})
    repo.save_branch_graph = AsyncMock()
    repo.get_branch = AsyncMock(return_value=None)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc:
            await merge_branches(10, payload, session=session)
    assert exc.value.status_code == 500


# ============================================================================
# preview_merge
# ============================================================================


@pytest.mark.asyncio
async def test_preview_merge_no_conflict():
    session = make_session()
    branch_repo = MagicMock()
    branch_repo.get_branch = AsyncMock(
        side_effect=[make_branch(1, parent_id=None), make_branch(2, parent_id=1)])
    chapter_repo = MagicMock()
    chapter_repo.get_chapter = AsyncMock(
        side_effect=[SimpleNamespace(content="same"),
                     SimpleNamespace(content="same"),
                     SimpleNamespace(content="base")])
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2, merge_ep_num=3)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo, chapter_repo)
        result = await preview_merge(10, payload, session=session)
    assert result["can_merge"] is True
    assert result["has_conflict"] is False
    assert result["merged_content"] == "same"
    assert result["base_branch_id"] == 1


@pytest.mark.asyncio
async def test_preview_merge_with_conflict():
    session = make_session()
    branch_repo = MagicMock()
    branch_repo.get_branch = AsyncMock(
        side_effect=[make_branch(1), make_branch(2, parent_id=1)])
    chapter_repo = MagicMock()
    chapter_repo.get_chapter = AsyncMock(
        side_effect=[SimpleNamespace(content="source text"),
                     SimpleNamespace(content="target text"),
                     SimpleNamespace(content="base text")])
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2, merge_ep_num=3)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo, chapter_repo)
        result = await preview_merge(10, payload, session=session)
    assert result["can_merge"] is False
    assert result["has_conflict"] is True
    assert result["conflict_chunks"]
    assert result["merged_content"] is None


@pytest.mark.asyncio
async def test_preview_merge_branch_not_found_and_missing_chapters():
    session = make_session()
    branch_repo = MagicMock()
    branch_repo.get_branch = AsyncMock(side_effect=[None, None])
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2, merge_ep_num=3)
    with pytest.MonkeyPatch.context() as m:
        m.setattr(branches_module, "BranchRepository", lambda s: branch_repo)
        m.setattr(branches_module, "ChapterRepository", lambda s: MagicMock())
        with pytest.raises(HTTPException) as exc:
            await preview_merge(10, payload, session=session)
    assert exc.value.status_code == 404

    # Missing chapters -> empty contents, no conflict
    branch_repo.get_branch = AsyncMock(
        side_effect=[make_branch(1, parent_id=None), make_branch(2, parent_id=None)])
    chapter_repo = MagicMock()
    chapter_repo.get_chapter = AsyncMock(return_value=None)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, branch_repo, chapter_repo)
        result = await preview_merge(10, payload, session=session)
    assert result["can_merge"] is True
    assert result["merged_content"] == ""
    assert result["base_branch_id"] is None


# ============================================================================
# commit_branch_merge
# ============================================================================


@pytest.mark.asyncio
async def test_commit_branch_merge_success():
    session = make_session()
    res = SimpleNamespace(updated_chapters_count=3, committed_at="now")
    service = MagicMock()
    service.commit_merge = AsyncMock(return_value=res)
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2)
    with pytest.MonkeyPatch.context() as m:
        m.setattr(branches_module, "BranchMergeService", lambda s: service)
        result = await commit_branch_merge(10, payload, session=session)
    assert result.updated_chapters_count == 3
    service.commit_merge.assert_awaited_once_with(book_id=10, request=payload)


@pytest.mark.asyncio
async def test_commit_branch_merge_value_error():
    session = make_session()
    service = MagicMock()
    service.commit_merge = AsyncMock(side_effect=ValueError("bad request"))
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2)
    with pytest.MonkeyPatch.context() as m:
        m.setattr(branches_module, "BranchMergeService", lambda s: service)
        with pytest.raises(HTTPException) as exc:
            await commit_branch_merge(10, payload, session=session)
    assert exc.value.status_code == 400
    assert "bad request" in exc.value.detail


@pytest.mark.asyncio
async def test_commit_branch_merge_generic_error():
    session = make_session()
    service = MagicMock()
    service.commit_merge = AsyncMock(side_effect=RuntimeError("db"))
    payload = SimpleNamespace(source_branch_id=1, target_branch_id=2)
    with pytest.MonkeyPatch.context() as m:
        m.setattr(branches_module, "BranchMergeService", lambda s: service)
        with pytest.raises(HTTPException) as exc:
            await commit_branch_merge(10, payload, session=session)
    assert exc.value.status_code == 500


# ============================================================================
# play session
# ============================================================================


@pytest.mark.asyncio
async def test_start_play_session_success():
    session = make_session()
    repo = MagicMock()
    repo.get_branch = AsyncMock(return_value=make_branch(1, book_id=10))
    repo.load_branch_graph = AsyncMock(return_value={"entry_node_id": "n1"})
    repo.create_play_session = AsyncMock()
    payload = SimpleNamespace(book_id=10, branch_id=1)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await start_play_session(payload, session=session)
    assert result.current_node_id == "n1"
    assert result.status == "active"
    repo.create_play_session.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_play_session_branch_not_found():
    session = make_session()
    repo = MagicMock()
    repo.get_branch = AsyncMock(return_value=None)
    payload = SimpleNamespace(book_id=10, branch_id=999)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc:
            await start_play_session(payload, session=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_play_state_success():
    session = make_session()
    import uuid as uuid_module
    from datetime import datetime as dt
    session_id = str(uuid_module.uuid4())
    repo = MagicMock()
    repo.get_play_session = AsyncMock(
        return_value=SimpleNamespace(branch_id=1, book_id=10, current_node_id="n1",
                                     context_json={"ctx": 1}, save_points_json=[1, 2],
                                     status="active", updated_at=dt.utcnow()))
    repo.load_branch_graph = AsyncMock(return_value={
        "nodes": {"n1": {"choices": [{"text": "go"}]}}})
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await get_play_state(session_id, session=session)
        assert result.session_id == session_id
        assert result.current_node_id == "n1"
        assert result.current_node["choices"]
        assert result.context == {"ctx": 1}
        assert result.save_points_count == 2
        assert result.status == "active"
        # status=None -> default "active"
        repo.get_play_session = AsyncMock(
            return_value=SimpleNamespace(branch_id=1, book_id=10, current_node_id="n1",
                                         context_json=None, save_points_json=None,
                                         status=None, updated_at=None))
        result2 = await get_play_state(session_id, session=session)
        assert result2.status == "active"
        assert result2.context == {}
        assert result2.save_points_count == 0


def make_play_session(branch_id=1, book_id=10, current_node_id="n1",
                      context_json=None, save_points_json=None, status="active"):
    from datetime import datetime as dt
    return SimpleNamespace(branch_id=branch_id, book_id=book_id,
                           current_node_id=current_node_id,
                           context_json=context_json,
                           save_points_json=save_points_json,
                           status=status, updated_at=dt.utcnow())


@pytest.mark.asyncio
async def test_get_play_state_invalid_uuid_and_not_found():
    session = make_session()
    with pytest.MonkeyPatch.context() as m:
        with pytest.raises(HTTPException) as exc:
            await get_play_state("not-a-uuid", session=session)
    assert exc.value.status_code == 400

    import uuid as uuid_module
    session_id = str(uuid_module.uuid4())
    repo = MagicMock()
    repo.get_play_session = AsyncMock(return_value=None)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        with pytest.raises(HTTPException) as exc:
            await get_play_state(session_id, session=session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_play_state_no_graph():
    session = make_session()
    import uuid as uuid_module
    session_id = str(uuid_module.uuid4())
    repo = MagicMock()
    repo.get_play_session = AsyncMock(return_value=make_play_session(current_node_id=None))
    repo.load_branch_graph = AsyncMock(return_value=None)
    with pytest.MonkeyPatch.context() as m:
        patch_branch_repo(m, repo)
        result = await get_play_state(session_id, session=session)
    assert result.current_node == {}
    assert result.current_node_id is None
