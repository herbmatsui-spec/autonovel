"""IF ルート分岐管理用 FastAPI ルータ."""

from __future__ import annotations

import io
import logging
import uuid
import zipfile
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth import validate_api_key_or_raise
from src.backend.database.core import get_db_manager
from src.backend.database.repositories.branch import BranchRepository
from src.backend.schemas.branch import (
    BranchForkRequest,
    BranchGraphResponse,
    BranchMergeRequest,
    BranchResponse,
)
from src.backend.schemas.branch_play import (
    BranchPlayRequest,
    BranchPlayStateResponse,
    BranchPlayChooseRequest,
    BranchPlaySessionResponse,
    BranchPlayEndRequest,
    BranchPlayPlaythroughResponse,
)
from src.domain.models.branch import BranchDbModelCreate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/branches",
    tags=["branches"],
    dependencies=[Depends(validate_api_key_or_raise)],
)


async def get_branch_session() -> AsyncSession:
    """FastAPI Depends 用の AsyncSession プロバイダ."""
    mgr = get_db_manager()
    print(f"[router] manager session bind: {mgr.get_session().bind.url}", flush=True)
    session = mgr.get_session()
    try:
        yield session
    finally:
        await session.close()


def _to_response(model: Any) -> BranchResponse:
    return BranchResponse(
        id=model.id,
        book_id=model.book_id,
        name=model.name,
        parent_id=model.parent_id,
        fork_ep_num=model.fork_ep_num,
        created_at=model.created_at,
    )


def _validate_uuid(session_id: str) -> None:
    try:
        uuid.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid session_id (UUID required)")


@router.post("/", response_model=BranchResponse, status_code=201)
async def create_branch(
    payload: BranchDbModelCreate,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchResponse:
    """新規ブランチを作成."""
    repo = BranchRepository(session)
    branch_id = await repo.create_branch(
        book_id=payload.book_id,
        name=payload.name,
        parent_id=payload.parent_id,
        fork_ep_num=payload.fork_ep_num or 0,
    )
    if payload.graph_json is not None:
        await repo.save_branch_graph(branch_id, payload.graph_json)
    branch = await repo.get_branch(branch_id)
    if branch is None:
        raise HTTPException(status_code=500, detail="Branch creation failed")
    await session.commit()
    return _to_response(branch)


@router.get("/{book_id}", response_model=list[BranchResponse])
async def list_branches(
    book_id: int,
    session: AsyncSession = Depends(get_branch_session),
) -> list[BranchResponse]:
    """書籍配下の全ブランチをツリー順に取得."""
    repo = BranchRepository(session)
    branches = await repo.get_branch_tree(book_id)
    return [_to_response(b) for b in branches]


@router.get("/{book_id}/graph", response_model=BranchGraphResponse)
async def get_branch_graph(
    book_id: int,
    branch_id: int,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchGraphResponse:
    """IF グラフ JSON を取得. branch_id は必須."""
    repo = BranchRepository(session)
    graph = await repo.load_branch_graph(branch_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    return BranchGraphResponse(branch_id=branch_id, graph=graph)


@router.post("/{book_id}/fork", response_model=BranchResponse, status_code=201)
async def fork_branch(
    book_id: int,
    payload: BranchForkRequest,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchResponse:
    """既存ブランチから分岐をフォーク."""
    repo = BranchRepository(session)
    new_id = await repo.create_branch(
        book_id=book_id,
        name=payload.name,
        parent_id=payload.parent_id,
        fork_ep_num=payload.fork_ep_num,
    )
    branch = await repo.get_branch(new_id)
    if branch is None:
        raise HTTPException(status_code=500, detail="Fork failed")
    await session.commit()
    return _to_response(branch)


@router.post("/{book_id}/merge", response_model=BranchResponse)
async def merge_branches(
    book_id: int,
    payload: BranchMergeRequest,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchResponse:
    """2 ブランチを MERGE ノードで合流.

    既存 IF グラフの merge_ep_num 位置に MERGE ノードを追加し、
    target ブランチに保存する。
    """
    repo = BranchRepository(session)
    target = await repo.load_branch_graph(payload.target_branch_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target graph not found")

    merge_node_id = f"merge_ep{payload.merge_ep_num}"
    target.setdefault("nodes", {})
    target["nodes"][merge_node_id] = {
        "id": merge_node_id,
        "episode_num": payload.merge_ep_num,
        "content": f"Merged from branch {payload.source_branch_id}",
        "branch_type": "merge",
        "choices": [],
        "merge_target": merge_node_id,
        "metadata": {"source_branch_id": payload.source_branch_id},
        "parent_ids": [payload.source_branch_id, payload.target_branch_id],
    }
    await repo.save_branch_graph(payload.target_branch_id, target)

    branch = await repo.get_branch(payload.target_branch_id)
    if branch is None:
        raise HTTPException(status_code=500, detail="Merge failed")
    await session.commit()
    return _to_response(branch)


@router.put("/{book_id}/graph", response_model=BranchGraphResponse)
async def save_branch_graph(
    book_id: int,
    branch_id: int,
    graph: dict[str, Any],
    session: AsyncSession = Depends(get_branch_session),
) -> BranchGraphResponse:
    """IF グラフをブランチに保存."""
    repo = BranchRepository(session)
    branch = await repo.get_branch(branch_id)
    if branch is None or branch.book_id != book_id:
        raise HTTPException(status_code=404, detail="Branch not found")
    await repo.save_branch_graph(branch_id, graph)
    await session.commit()
    return BranchGraphResponse(branch_id=branch_id, graph=graph)


# ============================================================================
# Player Session REST API (Episode 3: S25-S36)
# ============================================================================


@router.post("/play", response_model=BranchPlaySessionResponse, status_code=201)
async def start_play_session(
    payload: BranchPlayRequest,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchPlaySessionResponse:
    """IF プレイヤーセッションを開始. session_id は UUID で自動発行."""
    repo = BranchRepository(session)
    branch = await repo.get_branch(payload.branch_id)
    if branch is None or branch.book_id != payload.book_id:
        raise HTTPException(status_code=404, detail="Branch not found for book")

    graph = await repo.load_branch_graph(payload.branch_id)
    current_node_id = (graph or {}).get("entry_node_id") or None

    session_id = str(uuid.uuid4())
    await repo.create_play_session(
        session_id=session_id,
        book_id=payload.book_id,
        branch_id=payload.branch_id,
        current_node_id=current_node_id,
    )
    await session.commit()
    return BranchPlaySessionResponse(
        session_id=session_id,
        book_id=payload.book_id,
        branch_id=payload.branch_id,
        current_node_id=current_node_id,
        status="active",
        updated_at=datetime.utcnow(),
    )


@router.get("/play/{session_id}/state", response_model=BranchPlayStateResponse)
async def get_play_state(
    session_id: str,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchPlayStateResponse:
    """セッションの現状態（current node / context / available choices）を取得."""
    _validate_uuid(session_id)
    repo = BranchRepository(session)
    sess = await repo.get_play_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    graph = await repo.load_branch_graph(sess.branch_id) or {}
    nodes = graph.get("nodes", {}) or {}
    current = nodes.get(sess.current_node_id or "") or {}
    available_choices = current.get("choices", []) or []

    return BranchPlayStateResponse(
        session_id=session_id,
        book_id=sess.book_id,
        branch_id=sess.branch_id,
        current_node=current,
        current_node_id=sess.current_node_id,
        context=sess.context_json or {},
        available_choices=available_choices,
        save_points_count=len(sess.save_points_json or []),
        status=sess.status or "active",
        updated_at=sess.updated_at or datetime.utcnow(),
    )


@router.post("/play/{session_id}/choose", response_model=BranchPlayStateResponse)
async def play_choose(
    session_id: str,
    payload: BranchPlayChooseRequest,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchPlayStateResponse:
    """選択肢を実行し current_node を進める. 楽観ロック対応."""
    _validate_uuid(session_id)
    repo = BranchRepository(session)
    sess = await repo.get_play_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.status and sess.status != "active":
        raise HTTPException(status_code=409, detail=f"Session not active (status={sess.status})")

    graph = await repo.load_branch_graph(sess.branch_id) or {}
    nodes = graph.get("nodes", {}) or {}
    current = nodes.get(sess.current_node_id or "") or {}
    choices = current.get("choices", []) or []

    chosen = next((c for c in choices if c.get("id") == payload.choice_id), None)
    if chosen is None:
        raise HTTPException(status_code=400, detail="Choice not available from current node")

    new_node_id = chosen.get("target_node_id") or sess.current_node_id
    context = dict(sess.context_json or {})
    for k, v in (chosen.get("effects") or {}).items():
        context[k] = v
    context.setdefault("history", []).append(
        {"from": sess.current_node_id, "choice_id": payload.choice_id, "to": new_node_id}
    )

    expected_version = sess.version or 1
    ok = await repo.update_play_session_state_optimistic(
        session_id=session_id,
        expected_version=expected_version,
        current_node_id=new_node_id,
        context_json=context,
        save_points_json=list(sess.save_points_json or []),
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Concurrent modification detected")
    await session.commit()

    return await get_play_state(session_id, session)


@router.post("/play/{session_id}/save", response_model=BranchPlayStateResponse)
async def play_save(
    session_id: str,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchPlayStateResponse:
    """現状態を save_points に追記保存."""
    _validate_uuid(session_id)
    repo = BranchRepository(session)
    sess = await repo.get_play_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    save_points = list(sess.save_points_json or [])
    save_points.append(
        {
            "node_id": sess.current_node_id,
            "context": sess.context_json or {},
            "saved_at": datetime.utcnow().isoformat(),
        }
    )
    await repo.update_play_session_state(
        session_id=session_id,
        current_node_id=sess.current_node_id,
        context_json=sess.context_json or {},
        save_points_json=save_points,
    )
    await session.commit()
    return await get_play_state(session_id, session)


@router.post("/play/{session_id}/load", response_model=BranchPlayStateResponse)
async def play_load(
    session_id: str,
    index: int = 0,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchPlayStateResponse:
    """save_points の index から状態を復元."""
    _validate_uuid(session_id)
    repo = BranchRepository(session)
    sess = await repo.get_play_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    save_points = list(sess.save_points_json or [])
    if not (0 <= index < len(save_points)):
        raise HTTPException(
            status_code=400, detail=f"Save index out of range (0-{len(save_points) - 1})"
        )

    save = save_points[index]
    await repo.update_play_session_state(
        session_id=session_id,
        current_node_id=save.get("node_id"),
        context_json=save.get("context", {}),
        save_points_json=save_points,
    )
    await session.commit()
    return await get_play_state(session_id, session)


@router.post("/play/{session_id}/end", response_model=BranchPlaySessionResponse)
async def play_end(
    session_id: str,
    payload: BranchPlayEndRequest | None = None,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchPlaySessionResponse:
    """セッションを終了（status 更新）."""
    _validate_uuid(session_id)
    repo = BranchRepository(session)
    sess = await repo.get_play_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    new_status = (payload.status if payload else None) or "completed"
    await repo.end_play_session(session_id, status=new_status)
    await session.commit()

    return BranchPlaySessionResponse(
        session_id=session_id,
        book_id=sess.book_id,
        branch_id=sess.branch_id,
        current_node_id=sess.current_node_id,
        status=new_status,
        updated_at=datetime.utcnow(),
    )


@router.get("/play/{session_id}/playthrough", response_model=BranchPlayPlaythroughResponse)
async def get_playthrough(
    session_id: str,
    session: AsyncSession = Depends(get_branch_session),
) -> BranchPlayPlaythroughResponse:
    """プレイスルー記録 (history + context) を取得."""
    _validate_uuid(session_id)
    repo = BranchRepository(session)
    sess = await repo.get_play_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    ctx = sess.context_json or {}
    return BranchPlayPlaythroughResponse(
        session_id=session_id,
        book_id=sess.book_id,
        branch_id=sess.branch_id,
        history=ctx.get("history", []),
        flags=ctx.get("flags", {}),
        variables=ctx.get("variables", {}),
        final_ending=ctx.get("ending"),
        saved_at=datetime.utcnow(),
    )


@router.get("/{book_id}/nodes", response_model=dict)
async def list_branch_nodes(
    book_id: int,
    branch_id: int,
    session: AsyncSession = Depends(get_branch_session),
) -> dict[str, Any]:
    """ブランチのグラフに含まれるノード一覧を返す."""
    repo = BranchRepository(session)
    graph = await repo.load_branch_graph(branch_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    return {
        "branch_id": branch_id,
        "entry_node_id": graph.get("entry_node_id"),
        "nodes": graph.get("nodes", {}) or {},
    }


@router.post("/{book_id}/nodes", response_model=dict)
async def create_branch_node(
    book_id: int,
    branch_id: int,
    node: dict[str, Any],
    session: AsyncSession = Depends(get_branch_session),
) -> dict[str, Any]:
    """グラフに新ノードを追加."""
    if "id" not in node:
        raise HTTPException(status_code=422, detail="node.id is required")
    repo = BranchRepository(session)
    graph = await repo.load_branch_graph(branch_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    nodes = graph.setdefault("nodes", {})
    nodes[node["id"]] = node
    if not graph.get("entry_node_id"):
        graph["entry_node_id"] = node["id"]
    await repo.save_branch_graph(branch_id, graph)
    await session.commit()
    return {"branch_id": branch_id, "node": node}


@router.delete("/{book_id}/nodes/{node_id}", response_model=dict)
async def delete_branch_node(
    book_id: int,
    branch_id: int,
    node_id: str,
    session: AsyncSession = Depends(get_branch_session),
) -> dict[str, Any]:
    """ノード削除（孤立チェック付き）."""
    repo = BranchRepository(session)
    graph = await repo.load_branch_graph(branch_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    nodes = graph.get("nodes", {}) or {}
    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    # 孤立チェック: 他ノードから参照されていないか
    referenced_by: list[str] = []
    for nid, n in nodes.items():
        for choice in n.get("choices", []) or []:
            if choice.get("target_node_id") == node_id:
                referenced_by.append(nid)
    if referenced_by:
        raise HTTPException(
            status_code=422,
            detail=f"Node {node_id} is referenced by {referenced_by}; remove references first",
        )

    del nodes[node_id]
    if graph.get("entry_node_id") == node_id:
        graph["entry_node_id"] = next(iter(nodes.keys()), "")
    await repo.save_branch_graph(branch_id, graph)
    await session.commit()
    return {"branch_id": branch_id, "deleted": node_id}


@router.post("/{book_id}/editor/validate", response_model=dict)
async def validate_branch_graph(
    book_id: int,
    branch_id: int,
    session: AsyncSession = Depends(get_branch_session),
) -> dict[str, Any]:
    """グラフ整合性検証. errors: 問題箇所のリスト."""
    repo = BranchRepository(session)
    graph = await repo.load_branch_graph(branch_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")

    nodes = graph.get("nodes", {}) or {}
    errors: list[str] = []

    # エントリーノード存在
    entry = graph.get("entry_node_id", "")
    if not entry:
        errors.append("entry_node_id is empty")
    elif entry not in nodes:
        errors.append(f"Entry node {entry} not found")

    # 到達可能性
    reachable: set[str] = set()

    def traverse(node_id: str, path: list[str]) -> None:
        if node_id in path:
            errors.append(f"Cycle detected: {' -> '.join(path + [node_id])}")
            return
        if node_id not in nodes:
            errors.append(f"Target node {node_id} not found")
            return
        if node_id in reachable:
            return
        reachable.add(node_id)
        node = nodes[node_id]
        for choice in node.get("choices", []) or []:
            target = choice.get("target_node_id")
            if target:
                traverse(target, path + [node_id])
        merge_target = node.get("merge_target")
        if merge_target and merge_target != node_id:
            traverse(merge_target, path + [node_id])

    if entry and entry in nodes:
        traverse(entry, [])

    for nid in nodes:
        if nid not in reachable:
            errors.append(f"Unreachable node: {nid}")

    return {"branch_id": branch_id, "valid": len(errors) == 0, "errors": errors}


# ============================================================================
# WebSocket Player (Episode 5: S49-S54)
# ============================================================================


async def _load_state_dict(repo: BranchRepository, sess: Any) -> dict[str, Any]:
    graph = await repo.load_branch_graph(sess.branch_id) or {}
    nodes = graph.get("nodes", {}) or {}
    current = nodes.get(sess.current_node_id or "") or {}
    available_choices = current.get("choices", []) or []
    return {
        "type": "state",
        "session_id": sess.id,
        "current_node_id": sess.current_node_id,
        "current_node": current,
        "available_choices": available_choices,
        "context": sess.context_json or {},
        "save_points_count": len(sess.save_points_json or []),
        "status": sess.status or "active",
    }


@router.websocket("/play/{session_id}/ws")
async def play_ws(websocket: WebSocket, session_id: str) -> None:
    """IF プレイヤー双方向 WebSocket.

    クライアント → サーバー: {"action": "choose"|"save"|"load"|"end", ...}
    サーバー → クライアント: {"type": "state"|"error"|"closed", ...}
    """
    try:
        uuid.UUID(session_id)
    except (ValueError, AttributeError):
        await websocket.close(code=4000)
        return

    await websocket.accept()

    mgr = get_db_manager()
    session = mgr.get_session()
    try:
        repo = BranchRepository(session)
        sess = await repo.get_play_session(session_id)
        if sess is None:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close(code=4404)
            return

        # 初期 state を push
        await websocket.send_json(await _load_state_dict(repo, sess))

        while True:
            data = await websocket.receive_json()
            action = (data or {}).get("action")

            if action == "choose":
                choice_id = data.get("choice_id")
                if not choice_id:
                    await websocket.send_json({"type": "error", "message": "choice_id required"})
                    continue

                if sess.status and sess.status != "active":
                    await websocket.send_json(
                        {"type": "error", "message": f"Session not active (status={sess.status})"}
                    )
                    continue

                graph = await repo.load_branch_graph(sess.branch_id) or {}
                nodes = graph.get("nodes", {}) or {}
                current = nodes.get(sess.current_node_id or "") or {}
                choices = current.get("choices", []) or []
                chosen = next((c for c in choices if c.get("id") == choice_id), None)
                if chosen is None:
                    await websocket.send_json(
                        {"type": "error", "message": "Choice not available"}
                    )
                    continue

                new_node_id = chosen.get("target_node_id") or sess.current_node_id
                context = dict(sess.context_json or {})
                for k, v in (chosen.get("effects") or {}).items():
                    context[k] = v
                context.setdefault("history", []).append(
                    {"from": sess.current_node_id, "choice_id": choice_id, "to": new_node_id}
                )

                expected_version = sess.version or 1
                ok = await repo.update_play_session_state_optimistic(
                    session_id=session_id,
                    expected_version=expected_version,
                    current_node_id=new_node_id,
                    context_json=context,
                    save_points_json=list(sess.save_points_json or []),
                )
                if not ok:
                    await websocket.send_json(
                        {"type": "error", "message": "Concurrent modification"}
                    )
                    continue
                await session.commit()

                # reload
                sess = await repo.get_play_session(session_id)
                await websocket.send_json(await _load_state_dict(repo, sess))

            elif action == "save":
                save_points = list(sess.save_points_json or [])
                save_points.append(
                    {
                        "node_id": sess.current_node_id,
                        "context": sess.context_json or {},
                        "saved_at": datetime.utcnow().isoformat(),
                    }
                )
                await repo.update_play_session_state(
                    session_id=session_id,
                    current_node_id=sess.current_node_id,
                    context_json=sess.context_json or {},
                    save_points_json=save_points,
                )
                await session.commit()
                sess = await repo.get_play_session(session_id)
                await websocket.send_json(await _load_state_dict(repo, sess))

            elif action == "load":
                index = int(data.get("index", 0))
                save_points = list(sess.save_points_json or [])
                if not (0 <= index < len(save_points)):
                    await websocket.send_json(
                        {"type": "error", "message": f"Save index out of range (0-{len(save_points)-1})"}
                    )
                    continue
                save = save_points[index]
                await repo.update_play_session_state(
                    session_id=session_id,
                    current_node_id=save.get("node_id"),
                    context_json=save.get("context", {}),
                    save_points_json=save_points,
                )
                await session.commit()
                sess = await repo.get_play_session(session_id)
                await websocket.send_json(await _load_state_dict(repo, sess))

            elif action == "end":
                status = data.get("status", "completed")
                await repo.end_play_session(session_id, status=status)
                await session.commit()
                await websocket.send_json({"type": "closed", "status": status})
                await websocket.close(code=1000)
                break

            else:
                await websocket.send_json(
                    {"type": "error", "message": f"Unknown action: {action}"}
                )

    except WebSocketDisconnect:
        logger.info("ws disconnected session_id=%s", session_id)
    except Exception as exc:
        logger.exception("ws error session_id=%s: %s", session_id, exc)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        await session.close()


# ============================================================================
# EPUB Export (Episode 6: S61-S66)
# ============================================================================


def _minimal_epub(branch_name: str, nodes_in_order: list[dict[str, Any]]) -> bytes:
    """最小限の EPUB 3 を bytes で生成.

    nodes_in_order: [{"id": "n1", "episode_num": 1, "content": "..."}]
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype は無圧縮で先頭に配置
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        # META-INF/container.xml
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )
        # content.opf
        spine_items = "\n".join(
            f'    <itemref idref="ch{i+1}"/>' for i in range(len(nodes_in_order))
        )
        manifest_items = "\n".join(
            f'    <item id="ch{i+1}" href="ch{i+1}.xhtml" media-type="application/xhtml+xml"/>'
            for i in range(len(nodes_in_order))
        )
        zf.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{branch_name}</dc:title>
    <dc:identifier id="bid">urn:uuid:{uuid.uuid4()}</dc:identifier>
    <dc:language>ja</dc:language>
    <meta property="dcterms:modified">{datetime.utcnow().isoformat()}Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
{manifest_items}
  </manifest>
  <spine>
{spine_items}
  </spine>
</package>""",
        )
        # nav.xhtml
        nav_items_list = []
        for i, n in enumerate(nodes_in_order):
            nav_items_list.append(f'    <li><a href="ch{i+1}.xhtml">第{n.get("episode_num", i+1)}話</a></li>')
        nav_items = "\n".join(nav_items_list)
        zf.writestr(
            "OEBPS/nav.xhtml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>目次</title></head>
<body>
  <nav epub:type="toc">
    <ol>
{nav_items}
    </ol>
  </nav>
</body>
</html>""",
        )
        # 各チャプター xhtml
        for i, n in enumerate(nodes_in_order):
            content = (n.get("content") or "").replace("<", "&lt;").replace(">", "&gt;")
            zf.writestr(
                f"OEBPS/ch{i+1}.xhtml",
                f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>第{n.get("episode_num", i+1)}話</title></head>
<body>
  <h1>第{n.get("episode_num", i+1)}話</h1>
  <p>{content}</p>
</body>
</html>""",
            )
    return buf.getvalue()


def _topological_order(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """entry_node_id 起点で episode_num 昇順にノードを並べる."""
    nodes = graph.get("nodes", {}) or {}
    entry = graph.get("entry_node_id", "")
    visited: set[str] = set()
    order: list[dict[str, Any]] = []

    def traverse(nid: str) -> None:
        if nid in visited or nid not in nodes:
            return
        visited.add(nid)
        n = nodes[nid]
        order.append(n)
        for choice in n.get("choices", []) or []:
            target = choice.get("target_node_id")
            if target:
                traverse(target)
        merge_target = n.get("merge_target")
        if merge_target and merge_target != nid:
            traverse(merge_target)

    if entry:
        traverse(entry)
    # 残った未到達ノードも追加（バリデーション済み想定）
    for nid in sorted(nodes.keys()):
        if nid not in visited:
            order.append(nodes[nid])

    order.sort(key=lambda x: x.get("episode_num", 0))
    return order


@router.get("/{book_id}/export", response_class=Response)
async def export_branches_zip(
    book_id: int,
    session: AsyncSession = Depends(get_branch_session),
) -> Response:
    """書籍の全ブランチを EPUB に変換し ZIP で返す (基本スジ分割)."""
    repo = BranchRepository(session)
    branches = await repo.get_branch_tree(book_id)
    if not branches:
        raise HTTPException(status_code=404, detail="No branches for book")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for branch in branches:
            graph = await repo.load_branch_graph(branch.id)
            if graph is None:
                continue
            nodes = _topological_order(graph)
            epub_bytes = _minimal_epub(branch.name, nodes)
            # ファイル名安全化
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in branch.name)
            zf.writestr(f"branch_{branch.id}_{safe_name}.epub", epub_bytes)

    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="branches_{book_id}.zip"'},
    )


# ============================================================================
# Stats (Episode 6: S67-S69)
# ============================================================================


@router.get("/{book_id}/stats", response_model=dict)
async def get_branch_stats(
    book_id: int,
    session: AsyncSession = Depends(get_branch_session),
) -> dict[str, Any]:
    """選択率・平均到達ノード等の統計."""
    repo = BranchRepository(session)
    branches = await repo.get_branch_tree(book_id)
    sessions = await repo.list_play_sessions(book_id)

    total_sessions = len(sessions)
    completed = sum(1 for s in sessions if (s.status or "") == "completed")
    abandoned = sum(1 for s in sessions if (s.status or "") == "abandoned")

    # history から総選択数
    total_choices = 0
    unique_paths: set[tuple[str, ...]] = set()
    for s in sessions:
        ctx = s.context_json or {}
        history = ctx.get("history", [])
        total_choices += len(history)
        unique_paths.add(tuple(h.get("to", "") for h in history))

    return {
        "book_id": book_id,
        "branch_count": len(branches),
        "session_total": total_sessions,
        "session_completed": completed,
        "session_abandoned": abandoned,
        "session_active": total_sessions - completed - abandoned,
        "total_choices": total_choices,
        "unique_paths": len(unique_paths),
    }


@router.get("/{book_id}/choices", response_model=dict)
async def get_branch_choice_stats(
    book_id: int,
    session: AsyncSession = Depends(get_branch_session),
) -> dict[str, Any]:
    """選択肢ごとの選択数. choice_id → 集計."""
    repo = BranchRepository(session)
    sessions = await repo.list_play_sessions(book_id)

    counts: dict[str, int] = {}
    for s in sessions:
        ctx = s.context_json or {}
        for entry in ctx.get("history", []):
            cid = entry.get("choice_id")
            if cid:
                counts[cid] = counts.get(cid, 0) + 1

    return {
        "book_id": book_id,
        "choice_counts": counts,
        "total_choices": sum(counts.values()),
    }
