"""ナレッジグラフ可視化・クエリ・GraphRAG操作用 API ルーター."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.backend import database
from src.backend.config import settings
from src.infrastructure.database.models.chunk import ChapterChunk
from src.services.age_client import age_client
from src.services.graph_pipeline import graph_pipeline_service
from src.services.rag_service import rag_service

router = APIRouter(prefix="/api/graph", tags=["graph"])

logger = logging.getLogger("graph_router")


# ============================================================
# Request/Response Models
# ============================================================


class CypherQueryRequest(BaseModel):
    """任意のCypherクエリ実行リクエスト."""

    query: str = Field(..., description="実行するCypherクエリ")
    graph_name: str | None = Field(None, description="対象グラフ名")
    parameters: dict[str, Any] | None = Field(None, description="クエリパラメータ")
    column_definition: str = Field("(result agtype)", description="戻り値カラム定義")


class CypherQueryResponse(BaseModel):
    """Cypherクエリ実行レスポンス."""

    records: list[dict[str, Any]]
    summary: dict[str, Any]
    execution_time_ms: float


class NodeUpsertRequest(BaseModel):
    """ノードUPSERTリクエスト."""

    label: str = Field(..., description="ノードラベル")
    name: str = Field(..., description="ノード名（ユニークキー）")
    properties: dict[str, Any] | None = Field(None, description="追加プロパティ")
    graph_name: str | None = Field(None, description="対象グラフ名")


class EdgeUpsertRequest(BaseModel):
    """エッジUPSERTリクエスト."""

    source_label: str = Field(..., description="始点ノードラベル")
    source_name: str = Field(..., description="始点ノード名")
    target_label: str = Field(..., description="終点ノードラベル")
    target_name: str = Field(..., description="終点ノード名")
    relation_type: str = Field(..., description="関係タイプ")
    properties: dict[str, Any] | None = Field(None, description="関係プロパティ")
    graph_name: str | None = Field(None, description="対象グラフ名")


class BatchUpsertRequest(BaseModel):
    """バッチUPSERTリクエスト."""

    nodes: list[NodeUpsertRequest] = Field(default_factory=list)
    edges: list[EdgeUpsertRequest] = Field(default_factory=list)
    graph_name: str | None = Field(None, description="対象グラフ名")


class BatchUpsertResponse(BaseModel):
    """バッチUPSERTレスポンス."""

    nodes_created: int
    edges_created: int
    errors: list[str] = Field(default_factory=list)


class GraphSearchRequest(BaseModel):
    """グラフ検索リクエスト."""

    node_name: str = Field(..., description="起点ノード名")
    max_depth: int = Field(2, ge=1, le=5, description="最大ホップ数")
    relationship_types: list[str] | None = Field(None, description="フィルタする関係タイプ")
    direction: str = Field("both", pattern="^(outgoing|incoming|both)$", description="方向")
    limit: int = Field(50, ge=1, le=200, description="最大取得件数")
    graph_name: str | None = Field(None, description="対象グラフ名")


class GraphStatsResponse(BaseModel):
    """グラフ統計レスポンス."""

    node_count: int
    edge_count: int
    labels: list[str]
    relationship_types: list[str]


class PipelineProcessRequest(BaseModel):
    """パイプライン処理リクエスト."""

    chapter_id: int = Field(..., description="チャプターID")
    chapter_text: str = Field(..., description="チャプターテキスト")
    idempotency_key: str | None = Field(None, description="冪等性キー")


class PipelineBatchRequest(BaseModel):
    """パイプラインバッチ処理リクエスト."""

    chapters: list[PipelineProcessRequest] = Field(..., min_items=1)
    continue_on_error: bool = Field(True, description="エラー時に継続")


class HybridSearchRequest(BaseModel):
    """ハイブリッド検索リクエスト."""

    query: str = Field(..., description="検索クエリ")
    core_entities: list[str] | None = Field(None, description="グラフ探索の起点エンティティ")
    top_k: int = Field(10, ge=1, le=50, description="返却件数")
    alpha: float = Field(0.5, ge=0.0, le=1.0, description="ベクトル検索の重み")
    beta: float = Field(0.3, ge=0.0, le=1.0, description="グラフ検索の重み")
    gamma: float = Field(0.2, ge=0.0, le=1.0, description="全文検索の重み")


class RagContextRequest(BaseModel):
    """RAGコンテキスト生成リクエスト."""

    current_prompt: str = Field(..., description="現在のプロンプト/クエリ")
    character_name: str = Field(..., description="主人公名")
    additional_entities: list[str] | None = Field(None, description="追加エンティティ")


# ============================================================
# Graph Visualization & Query Endpoints
# ============================================================


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
                {
                    "id": "主人公",
                    "label": "Character",
                    "properties": {"description": "物語の主人公", "is_alive": True},
                },
                {
                    "id": "王都ルミナス",
                    "label": "Location",
                    "properties": {"description": "物語の舞台となる大都市"},
                },
                {"id": "聖剣", "label": "Item", "properties": {"description": "伝説の武器"}},
            ],
            "edges": [
                {
                    "source": "主人公",
                    "target": "王都ルミナス",
                    "type": "LOCATED_IN",
                    "properties": {"detail": "滞在中"},
                },
                {
                    "source": "主人公",
                    "target": "聖剣",
                    "type": "POSSESSES",
                    "properties": {"detail": "所持"},
                },
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
            nodes.append(
                {
                    "id": node_name,
                    "label": row[1],
                    "properties": row[3],
                }
            )

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
            edges.append(
                {
                    "source": str(row[0]).strip('"'),
                    "type": str(row[1]).strip('"'),
                    "target": str(row[2]).strip('"'),
                    "properties": row[3],
                }
            )

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


# ============================================================
# Cypher Query Endpoint
# ============================================================


@router.post("/cypher", response_model=CypherQueryResponse)
def execute_cypher(
    request: CypherQueryRequest,
    session: Session = Depends(database.get_db),
) -> CypherQueryResponse:
    """任意のCypherクエリを実行する（管理者向け）."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    try:
        result = age_client.execute_cypher(
            session=session,
            cypher_query=request.query,
            column_definition=request.column_definition,
            graph_name=request.graph_name,
            parameters=request.parameters,
        )
        return CypherQueryResponse(
            records=result.records,
            summary=result.summary,
            execution_time_ms=result.execution_time_ms,
        )
    except Exception as e:
        logger.error("Cypher execution failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Graph Mutation Endpoints
# ============================================================


@router.post("/nodes", status_code=201)
def upsert_node(
    request: NodeUpsertRequest,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """ノードを作成または更新する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    success = age_client.upsert_node(
        session=session,
        label=request.label,
        name=request.name,
        properties=request.properties,
        graph_name=request.graph_name,
    )
    if success:
        session.commit()
        return {"success": True, "label": request.label, "name": request.name}
    else:
        raise HTTPException(status_code=500, detail="Failed to upsert node")


@router.post("/edges", status_code=201)
def upsert_edge(
    request: EdgeUpsertRequest,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """エッジを作成または更新する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    success = age_client.upsert_edge(
        session=session,
        source_label=request.source_label,
        source_name=request.source_name,
        target_label=request.target_label,
        target_name=request.target_name,
        relation_type=request.relation_type,
        properties=request.properties,
        graph_name=request.graph_name,
    )
    if success:
        session.commit()
        return {"success": True, "relation": request.relation_type}
    else:
        raise HTTPException(status_code=500, detail="Failed to upsert edge")


@router.post("/batch", response_model=BatchUpsertResponse)
def upsert_batch(
    request: BatchUpsertRequest,
    session: Session = Depends(database.get_db),
) -> BatchUpsertResponse:
    """ノードとエッジをバッチで作成・更新する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    errors = []
    nodes_created = 0
    edges_created = 0

    # ノードのバッチUPSERT
    if request.nodes:
        node_dicts = [
            {"label": n.label, "name": n.name, "properties": n.properties} for n in request.nodes
        ]
        nodes_created = age_client.upsert_nodes_batch(
            session=session,
            nodes=node_dicts,
            graph_name=request.graph_name,
        )

    # エッジのバッチUPSERT
    if request.edges:
        edge_dicts = [
            {
                "source_label": e.source_label,
                "source_name": e.source_name,
                "target_label": e.target_label,
                "target_name": e.target_name,
                "relation_type": e.relation_type,
                "properties": e.properties,
            }
            for e in request.edges
        ]
        edges_created = age_client.upsert_edges_batch(
            session=session,
            edges=edge_dicts,
            graph_name=request.graph_name,
        )

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        errors.append(f"Commit failed: {e}")

    return BatchUpsertResponse(
        nodes_created=nodes_created,
        edges_created=edges_created,
        errors=errors,
    )


@router.delete("/nodes/{label}/{name}")
def delete_node(
    label: str,
    name: str,
    graph_name: str | None = Query(None),
    detach: bool = Query(True, description="関連エッジも削除"),
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """ノードを削除する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    success = age_client.delete_node(
        session=session,
        label=label,
        name=name,
        graph_name=graph_name,
        detach=detach,
    )
    if success:
        session.commit()
        return {"success": True, "label": label, "name": name}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete node")


# ============================================================
# Graph Search & Traversal Endpoints
# ============================================================


@router.post("/search/neighbors")
def search_neighbors(
    request: GraphSearchRequest,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """指定ノードからNホップ以内の近傍ノードを取得する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        return {"node_name": request.node_name, "neighbors": [], "count": 0}

    neighbors = age_client.get_neighbors(
        session=session,
        node_name=request.node_name,
        max_depth=request.max_depth,
        graph_name=request.graph_name,
        relationship_types=request.relationship_types,
        direction=request.direction,
        limit=request.limit,
    )

    return {
        "node_name": request.node_name,
        "neighbors": neighbors,
        "count": len(neighbors),
    }


@router.get("/nodes/{node_name}/path/{target_name}")
def get_shortest_path(
    node_name: str,
    target_name: str,
    max_depth: int = Query(5, ge=1, le=10),
    graph_name: str | None = Query(None),
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """2ノード間の最短パスを取得する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    path = age_client.get_shortest_path(
        session=session,
        source_name=node_name,
        target_name=target_name,
        max_depth=max_depth,
        graph_name=graph_name,
    )

    return {
        "source": node_name,
        "target": target_name,
        "path": path,
        "found": path is not None,
    }


@router.get("/stats", response_model=GraphStatsResponse)
def get_graph_stats(
    graph_name: str | None = Query(None),
    session: Session = Depends(database.get_db),
) -> GraphStatsResponse:
    """グラフの統計情報を取得する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    stats = age_client.get_graph_stats(session, graph_name)
    return GraphStatsResponse(
        node_count=stats.node_count,
        edge_count=stats.edge_count,
        labels=stats.labels,
        relationship_types=stats.relationship_types,
    )


@router.get("/labels")
def get_labels(
    graph_name: str | None = Query(None),
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """グラフ内の全ラベル一覧を取得する."""
    if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
        raise HTTPException(status_code=400, detail="GraphRAG is not enabled or not on PostgreSQL")

    try:
        gname = graph_name or settings.AGE_GRAPH_NAME
        query = "CALL ag_labels() YIELD name RETURN collect(name) as labels"
        result = age_client.execute_cypher(session, query, graph_name=gname)
        labels = result.records[0].get("labels", []) if result.records else []
        return {"labels": labels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GraphRAG Pipeline Endpoints
# ============================================================


@router.post("/pipeline/process", response_model=dict[str, Any])
def process_chapter(
    request: PipelineProcessRequest,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """単一チャプターのGraphRAG処理を実行する."""
    if not request.chapter_text.strip():
        return {"chunks_created": 0, "entities_created": 0, "relationships_created": 0}

    idempotency_key = request.idempotency_key or f"chapter_{request.chapter_id}"
    result = graph_pipeline_service.process_chapter_knowledge(
        session=session,
        chapter_id=request.chapter_id,
        chapter_text=request.chapter_text,
        idempotency_key=idempotency_key,
    )

    return {
        "chapter_id": result.chapter_id,
        "success": result.success,
        "chunks_created": result.chunks_created,
        "entities_created": result.entities_created,
        "relationships_created": result.relationships_created,
        "error": result.error,
        "idempotency_key": result.idempotency_key,
    }


@router.post("/pipeline/batch", response_model=dict[str, Any])
def process_chapters_batch(
    request: PipelineBatchRequest,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """複数チャプターのGraphRAG処理をバッチ実行する."""
    chapters = [(c.chapter_id, c.chapter_text) for c in request.chapters]
    stats = graph_pipeline_service.process_chapters_batch(
        session=session,
        chapters=chapters,
        continue_on_error=request.continue_on_error,
    )

    return {
        "chapters_processed": stats.chapters_processed,
        "chunks_created": stats.chunks_created,
        "entities_created": stats.entities_created,
        "relationships_created": stats.relationships_created,
        "errors": stats.errors,
        "elapsed_ms": stats.elapsed_ms(),
    }


@router.get("/pipeline/status")
def get_pipeline_status(
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """パイプラインの処理状態を取得する."""
    return graph_pipeline_service.get_pipeline_status(session)


# ============================================================
# Hybrid Search & RAG Context Endpoints
# ============================================================


@router.post("/rag/hybrid-search")
async def hybrid_search(
    request: HybridSearchRequest,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """ハイブリッド検索 (Vector + Graph + Fulltext) を実行する."""
    import time

    start = time.perf_counter()

    try:
        results = await rag_service.hybrid_search(
            session=session,
            query=request.query,
            core_entities=request.core_entities,
            top_k=request.top_k,
            alpha=request.alpha,
            beta=request.beta,
            gamma=request.gamma,
        )

        return {
            "query": request.query,
            "results": [
                {
                    "id": r.id,
                    "content": r.content,
                    "metadata": r.metadata,
                    "source": r.source,
                    "score": r.score,
                    "similarity": r.similarity,
                }
                for r in results
            ],
            "count": len(results),
            "elapsed_ms": int((time.perf_counter() - start) * 1000),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/context")
async def build_rag_context(
    request: RagContextRequest,
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """執筆用RAGコンテキスト (グラフ + ベクトル + 全文) を生成する."""
    try:
        context = await rag_service.build_rag_context(
            session=session,
            current_prompt=request.current_prompt,
            character_name=request.character_name,
            additional_entities=request.additional_entities,
        )

        return {
            "graph_context": context.graph_context,
            "vector_context": context.vector_context,
            "stats": context.stats,
            "token_estimate": context.token_estimate,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/episode")
async def retrieve_for_episode(
    book_id: int | None = None,
    episode_number: int | None = None,
    character_name: str = Query(..., description="主人公名"),
    additional_entities: list[str] | None = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    session: Session = Depends(database.get_db),
) -> dict[str, Any]:
    """エピソード執筆向けのコンテキストを一括取得する."""
    try:
        result = await rag_service.retrieve_for_episode(
            session=session,
            book_id=book_id,
            episode_number=episode_number,
            character_name=character_name,
            additional_entities=additional_entities,
            top_k=top_k,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/stats")
def get_rag_stats() -> dict[str, Any]:
    """RAGサービスの統計情報を取得する."""
    return rag_service.get_last_stats()


# graph_router エクスポート用
__all__ = ["router"]
