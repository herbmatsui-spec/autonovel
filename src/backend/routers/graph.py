"""ナレッジグラフ可視化およびクエリ用 API ルーター."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.backend import database
from src.backend.config import settings
from src.models.chunk import ChapterChunk
from src.services.age_client import age_client

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
def get_graph_data(
    graph_name: str | None = None,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """フロントエンドの相関図可視化 (Force-Graph 等) 用にノードとエッジ一覧を取得する."""
    gname = graph_name or settings.AGE_GRAPH_NAME

    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        # SQLite / モック環境用のサンプルフォールバックデータ
        return {
            "graph_name": gname,
            "nodes": [
                {"id": "主人公", "label": "Character", "properties": {"description": "物語の主人公", "is_alive": True}},
                {"id": "王都ルミナス", "label": "Location", "properties": {"description": "物語の舞台となる大都市"}},
                {"id": "聖剣", "label": "Item", "properties": {"description": "伝説の武器"}},
            ],
            "edges": [
                {"source": "主人公", "target": "王都ルミナス", "type": "LOCATED_IN", "properties": {"detail": "滞在中"}},
                {"source": "主人公", "target": "聖剣", "type": "POSSESSES", "properties": {"detail": "所持"}},
            ],
        }

    try:
        # 全ノードの取得
        node_query = "MATCH (n) RETURN id(n), labels(n), n.name, n"
        node_rows = age_client.execute_cypher(
            session=session,
            cypher_query=node_query,
            column_definition="(id agtype, labels agtype, name agtype, props agtype)",
            graph_name=gname,
        )

        nodes = []
        for row in node_rows:
            node_name = str(row[2]).strip('"') if row[2] else str(row[0])
            nodes.append({
                "id": node_name,
                "label": row[1],
                "properties": row[3],
            })

        # 全エッジの取得
        edge_query = "MATCH (a)-[r]->(b) RETURN a.name, type(r), b.name, r"
        edge_rows = age_client.execute_cypher(
            session=session,
            cypher_query=edge_query,
            column_definition="(source agtype, rel_type agtype, target agtype, props agtype)",
            graph_name=gname,
        )

        edges = []
        for row in edge_rows:
            edges.append({
                "source": str(row[0]).strip('"'),
                "type": str(row[1]).strip('"'),
                "target": str(row[2]).strip('"'),
                "properties": row[3],
            })

        return {
            "graph_name": gname,
            "nodes": nodes,
            "edges": edges,
        }
    except Exception as e:
        return {
            "graph_name": gname,
            "error": str(e),
            "nodes": [],
            "edges": [],
        }


@router.get("/chunks")
def list_chapter_chunks(
    chapter_id: int | None = Query(None, description="章IDでフィルタ"),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(database.get_db),
) -> list[dict[str, Any]]:
    """保存されているベクトルチャンク一覧を取得する."""
    query = session.query(ChapterChunk)
    if chapter_id is not None:
        query = query.filter(ChapterChunk.chapter_id == chapter_id)
    chunks = query.order_by(ChapterChunk.created_at.desc()).limit(limit).all()

    return [
        {
            "id": chunk.id,
            "chapter_id": chunk.chapter_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "has_embedding": chunk.embedding is not None,
            "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
        }
        for chunk in chunks
    ]
