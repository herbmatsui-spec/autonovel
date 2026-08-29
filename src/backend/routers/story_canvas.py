"""
routers/story_canvas.py - ストーリーキャンバス API

ノード・エッジの CRUD および既存データからの初期化（seed）を提供する。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.backend.database.models import Character, Plot
from src.backend.database.repositories.story_canvas_repo import StoryCanvasRepository
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.models.api_schemas import (
    CreateEdgeRequest,
    CreateNodeRequest,
    SeedCanvasRequest,
    StoryCanvasResponse,
    StoryEdgeSchema,
    StoryNodeSchema,
    UpdateNodeRequest,
)

router = APIRouter(prefix="/api/story_canvas", tags=["story_canvas"])


def get_repo() -> StoryCanvasRepository:
    return StoryCanvasRepository(AppContainer.db())


@router.get("/{book_id}", response_model=StoryCanvasResponse)
async def get_story_canvas(
    book_id: int,
    repo: StoryCanvasRepository = Depends(get_repo),
) -> StoryCanvasResponse:
    """指定作品のキャンバスデータ（nodes + edges）を取得する。"""
    return await repo.get_canvas(book_id)


@router.post("/{book_id}/nodes", response_model=StoryNodeSchema)
async def create_story_node(
    book_id: int,
    req: CreateNodeRequest,
    repo: StoryCanvasRepository = Depends(get_repo),
) -> StoryNodeSchema:
    """新規ノードを作成する。"""
    node = await repo.upsert_node(
        book_id=book_id,
        kind=req.kind,
        label=req.label,
        x=req.x,
        y=req.y,
        data=req.data,
        ep_num=req.ep_num,
        character_id=req.character_id,
    )
    return StoryNodeSchema(
        id=f"node-{node.id}",
        book_id=node.book_id,
        kind=node.kind,
        label=node.label,
        ep_num=node.ep_num,
        character_id=node.character_id,
        x=node.x,
        y=node.y,
        data=req.data or {},
    )


@router.put("/{book_id}/nodes", response_model=List[StoryNodeSchema])
async def update_story_nodes(
    book_id: int,
    reqs: List[UpdateNodeRequest],
    repo: StoryCanvasRepository = Depends(get_repo),
) -> List[StoryNodeSchema]:
    """複数ノードの座標・ラベル・データを一括更新する。"""
    updated: List[StoryNodeSchema] = []
    for req in reqs:
        # id 形式: "node-{db_id}" または数値
        node_id_str = req.id
        if node_id_str.startswith("node-"):
            node_id = int(node_id_str.split("-")[1])
        else:
            node_id = int(node_id_str)

        node = await repo.get_node_by_id(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {req.id} not found")

        node = await repo.upsert_node(
            book_id=book_id,
            kind=node.kind,
            label=req.label if req.label is not None else node.label,
            x=req.x if req.x is not None else node.x,
            y=req.y if req.y is not None else node.y,
            data=req.data if req.data is not None else node.data,
            ep_num=node.ep_num,
            character_id=node.character_id,
            node_id=node_id,
        )
        updated.append(
            StoryNodeSchema(
                id=f"node-{node.id}",
                book_id=node.book_id,
                kind=node.kind,
                label=node.label,
                ep_num=node.ep_num,
                character_id=node.character_id,
                x=node.x,
                y=node.y,
                data=node.data,
            )
        )
    return updated


@router.delete("/{book_id}/nodes/{node_id}")
async def delete_story_node(
    book_id: int,
    node_id: str,
    repo: StoryCanvasRepository = Depends(get_repo),
) -> Dict[str, bool]:
    """ノードを削除する。"""
    # id 形式: "node-{db_id}" または数値
    if node_id.startswith("node-"):
        db_id = int(node_id.split("-")[1])
    else:
        db_id = int(node_id)

    ok = await repo.delete_node(db_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return {"success": True}


@router.post("/{book_id}/edges", response_model=StoryEdgeSchema)
async def create_story_edge(
    book_id: int,
    req: CreateEdgeRequest,
    repo: StoryCanvasRepository = Depends(get_repo),
) -> StoryEdgeSchema:
    """新規エッジを作成する。"""
    edge = await repo.create_edge(
        book_id=book_id,
        source=req.source,
        target=req.target,
        kind=req.kind,
        data=req.data,
    )
    return StoryEdgeSchema(
        id=f"edge-{edge.id}",
        book_id=edge.book_id,
        source=edge.source,
        target=edge.target,
        kind=edge.kind,
        data=edge.data,
    )


@router.delete("/{book_id}/edges/{edge_id}")
async def delete_story_edge(
    book_id: int,
    edge_id: str,
    repo: StoryCanvasRepository = Depends(get_repo),
) -> Dict[str, bool]:
    """エッジを削除する。"""
    if edge_id.startswith("edge-"):
        db_id = int(edge_id.split("-")[1])
    else:
        db_id = int(edge_id)

    ok = await repo.delete_edge(db_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found")
    return {"success": True}


# ==========================================
# Seed (既存データから自動生成)
# ==========================================


@router.post("/{book_id}/seed", response_model=StoryCanvasResponse)
async def seed_story_canvas(
    book_id: int,
    req: SeedCanvasRequest = SeedCanvasRequest(),
    repo: StoryCanvasRepository = Depends(get_repo),
) -> StoryCanvasResponse:
    """既存の plots / characters / structure から初期キャンバスを生成する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        # 既存ノードをクリア
        await uow.session.execute(
            delete(StoryNode).where(StoryNode.book_id == book_id)
        )
        await uow.session.execute(
            delete(StoryEdge).where(StoryEdge.book_id == book_id)
        )

        nodes_created: List[StoryNodeSchema] = []
        edges_created: List[StoryEdgeSchema] = []

        # 1. Premise ノード（作品の核）
        premise_node = await repo.upsert_node(
            book_id=book_id,
            kind="premise",
            label="作品の核 (Premise)",
            x=400,
            y=100,
            data={"description": "作品の核となるコンセプト・あらすじ"},
        )
        nodes_created.append(
            StoryNodeSchema(
                id=f"node-{premise_node.id}",
                book_id=premise_node.book_id,
                kind=premise_node.kind,
                label=premise_node.label,
                x=premise_node.x,
                y=premise_node.y,
                data=premise_node.data,
            )
        )

        # 2. Act ノード（構造テンプレートから）
        if req.include_structure:
            act_names = ["第1幕: 導入", "第2幕: 展開", "第3幕: 結末"]
            for i, name in enumerate(act_names):
                act_node = await repo.upsert_node(
                    book_id=book_id,
                    kind="act",
                    label=name,
                    x=200 + i * 300,
                    y=250,
                    data={"structure": "three_act", "beat": ["setup", "confrontation", "resolution"][i]},
                )
                nodes_created.append(
                    StoryNodeSchema(
                        id=f"node-{act_node.id}",
                        book_id=act_node.book_id,
                        kind=act_node.kind,
                        label=act_node.label,
                        x=act_node.x,
                        y=act_node.y,
                        data=act_node.data,
                    )
                )
                # Premise -> Act エッジ
                edge = await repo.create_edge(
                    book_id=book_id,
                    source=f"node-{premise_node.id}",
                    target=f"node-{act_node.id}",
                    kind="part_of",
                )
                edges_created.append(
                    StoryEdgeSchema(
                        id=f"edge-{edge.id}",
                        book_id=edge.book_id,
                        source=edge.source,
                        target=edge.target,
                        kind=edge.kind,
                        data=edge.data,
                    )
                )

        # 3. Episode ノード（Plot から）
        if req.include_plots:
            result = await uow.session.execute(
                select(Plot).where(Plot.book_id == book_id).order_by(Plot.ep_num)
            )
            plots = result.scalars().all()

            act_nodes = [n for n in nodes_created if n.kind == "act"]
            for plot in plots:
                # アクト割り当て（簡易: 話数で均等割り）
                act_idx = min((plot.ep_num - 1) * len(act_nodes) // max(1, len(plots) or 1), len(act_nodes) - 1)
                act_node_id = act_nodes[act_idx].id if act_nodes else None

                ep_node = await repo.upsert_node(
                    book_id=book_id,
                    kind="episode",
                    label=f"EP{plot.ep_num}: {plot.title or '無題'}",
                    x=100 + (plot.ep_num % 5) * 180,
                    y=450 + (plot.ep_num // 5) * 120,
                    ep_num=plot.ep_num,
                    data={
                        "tension": plot.tension or 50,
                        "is_catharsis": plot.is_catharsis,
                        "next_hook": plot.next_hook or "{}",
                        "summary": plot.summary or "",
                        "detailed_blueprint": plot.detailed_blueprint or "",
                    },
                )
                nodes_created.append(
                    StoryNodeSchema(
                        id=f"node-{ep_node.id}",
                        book_id=ep_node.book_id,
                        kind=ep_node.kind,
                        label=ep_node.label,
                        ep_num=ep_node.ep_num,
                        x=ep_node.x,
                        y=ep_node.y,
                        data=ep_node.data,
                    )
                )

                # Act -> Episode エッジ
                if act_node_id:
                    edge = await repo.create_edge(
                        book_id=book_id,
                        source=act_node_id,
                        target=f"node-{ep_node.id}",
                        kind="part_of",
                    )
                    edges_created.append(
                        StoryEdgeSchema(
                            id=f"edge-{edge.id}",
                            book_id=edge.book_id,
                            source=edge.source,
                            target=edge.target,
                            kind=edge.kind,
                            data=edge.data,
                        )
                    )

                # 前エピソード -> 現在エピソード (flow エッジ)
                if plot.ep_num > 1:
                    prev_ep_nodes = [n for n in nodes_created if n.kind == "episode" and n.ep_num == plot.ep_num - 1]
                    if prev_ep_nodes:
                        edge = await repo.create_edge(
                            book_id=book_id,
                            source=prev_ep_nodes[0].id,
                            target=f"node-{ep_node.id}",
                            kind="flow",
                        )
                        edges_created.append(
                            StoryEdgeSchema(
                                id=f"edge-{edge.id}",
                                book_id=edge.book_id,
                                source=edge.source,
                                target=edge.target,
                                kind=edge.kind,
                                data=edge.data,
                            )
                        )

        # 4. Character ノード（Character から）
        if req.include_characters:
            result = await uow.session.execute(
                select(Character).where(Character.book_id == book_id)
            )
            characters = result.scalars().all()

            for idx, char in enumerate(characters):
                reg = {}
                if char.registry_data:
                    try:
                        reg = json.loads(char.registry_data)
                    except (json.JSONDecodeError, TypeError):
                        pass

                char_node = await repo.upsert_node(
                    book_id=book_id,
                    kind="character",
                    label=char.name or f"キャラクター{char.id}",
                    x=800 + (idx % 3) * 150,
                    y=250 + (idx // 3) * 150,
                    character_id=char.id,
                    data={
                        "role": char.role or "",
                        "traits": reg.get("traits", []),
                        "relationships": reg.get("relationships", {}),
                        "background": reg.get("background", ""),
                    },
                )
                nodes_created.append(
                    StoryNodeSchema(
                        id=f"node-{char_node.id}",
                        book_id=char_node.book_id,
                        kind=char_node.kind,
                        label=char_node.label,
                        character_id=char_node.character_id,
                        x=char_node.x,
                        y=char_node.y,
                        data=char_node.data,
                    )
                )

                # キャラクターが担当するエピソードがあれば pov エッジ
                if char.id:
                    ep_nodes = [n for n in nodes_created if n.kind == "episode" and n.data.get("pov_character_id") == char.id]
                    # 注: Plot.pov_character_id 参照（実装時は Plot から取得）
                    # ここでは簡易的に最初のエピソードに接続
                    if ep_nodes:
                        pass  # 実装は後で

        return StoryCanvasResponse(nodes=nodes_created, edges=edges_created)


# 依存インポート（下部で回避）
from sqlalchemy import delete
import json