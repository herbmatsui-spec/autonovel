"""Phase 2 Admin APIs for Audit and Reflective RAG."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.core.container import AppContainer
from src.config.audit_weights import load_weights
from src.services.audit_aggregator import AuditAggregator
from src.services.rag_service import rag_service
from src.services.reflective_rag import ReflectiveRAGService
from src.agents.specialists import (
    ConsistencyAuditor,
    CreativityAuditor,
    ReaderHookAuditor,
    EmotionCurveAuditor,
    StyleAuditor,
    FactualAuditor,
    StructureAuditor,
    MultimodalAuditor,
)

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


async def get_session():
    """Dependency to get DB session from AppContainer."""
    from src.core.container import AppContainer
    db = AppContainer.db()
    async with db.get_session() as session:
        yield session

class AuditAggregateTestRequest(BaseModel):
    book_id: int = Field(..., description="対象書籍ID")
    chapter_number: int = Field(..., description="対象章番号")
    draft_text: str = Field(..., description="監査対象の原稿テキスト")
    world_bible_snapshot: dict[str, Any] = Field(default_factory=dict)
    style_dna: dict[str, Any] = Field(default_factory=dict)
    plot_tree: str = Field(default="")
    plot_summary: str = Field(default="")
    illustration_prompts: str = Field(default="")
    genre: str = Field(default="literary")
    phase: str = Field(default="mid_writing")


class AuditAggregateTestResponse(BaseModel):
    overall: float
    by_specialist: dict[str, float]
    missing: list[str]
    weights_used: dict[str, float]
    lowest_dimension: str | None


class SpecialistInfo(BaseModel):
    name: str
    version: str = "v2-phase2"
    llm_required: bool


# ---- Audit Admin Endpoints ----

@router.get("/specialists", response_model=list[SpecialistInfo])
async def list_specialists():
    """登録済みの専門オーディター一覧を取得"""
    return [
        SpecialistInfo(name="consistency", llm_required=False),
        SpecialistInfo(name="creativity", llm_required=False),
        SpecialistInfo(name="reader_hook", llm_required=False),
        SpecialistInfo(name="emotion_curve", llm_required=False),
        SpecialistInfo(name="style", llm_required=False),
        SpecialistInfo(name="factual", llm_required=True),
        SpecialistInfo(name="structure", llm_required=True),
        SpecialistInfo(name="multimodal", llm_required=True),
    ]


@router.post("/aggregate_test", response_model=AuditAggregateTestResponse)
async def test_aggregate(
    req: AuditAggregateTestRequest,
    session: AsyncSession = Depends(get_session),
):
    """任意の原稿で監査集約を実行（テスト用）"""
    # Load weights
    weights = load_weights(genre=req.genre, phase=req.phase)

    # Create specialists (no LLM for test)
    specialists = [
        ConsistencyAuditor(llm=None),
        CreativityAuditor(llm=None),
        ReaderHookAuditor(llm=None),
        EmotionCurveAuditor(llm=None),
        StyleAuditor(llm=None, style_profile=req.style_dna),
        FactualAuditor(llm=None),
        StructureAuditor(llm=None),
        MultimodalAuditor(llm=None),
    ]

    # Run aggregator
    aggregator = AuditAggregator(
        specialists=specialists,
        weights=weights,
        event_bus=None,
    )

    ctx = {
        "book_id": req.book_id,
        "chapter_number": req.chapter_number,
        "draft_text": req.draft_text,
        "world_bible_snapshot": req.world_bible_snapshot,
        "style_dna": req.style_dna,
        "plot_tree": req.plot_tree,
        "plot_summary": req.plot_summary,
        "illustration_prompts": req.illustration_prompts,
        "genre": req.genre,
        "correlation_id": f"admin_test_book{req.book_id}_ch{req.chapter_number}",
    }

    await aggregator.run_all(ctx)
    result = aggregator.aggregate()

    return AuditAggregateTestResponse(
        overall=result.overall,
        by_specialist=result.by_specialist,
        missing=result.missing,
        weights_used=result.weights_used,
        lowest_dimension=result.lowest_dimension(),
    )


@router.get("/weights")
async def get_audit_weights(
    genre: str | None = Query(None, description="ジャンルフィルタ"),
    phase: str | None = Query(None, description="フェーズフィルタ"),
):
    """現在の重み設定を取得"""
    weights = load_weights(genre=genre, phase=phase)
    return {
        "weights": weights,
        "genre": genre,
        "phase": phase,
    }


# ---- Reflective RAG Admin ----

rag_router = APIRouter(prefix="/admin/rag", tags=["admin-rag"])


class ReflectionTestRequest(BaseModel):
    query: str = Field(..., description="検索クエリ")
    book_id: int | None = Field(None, description="書籍ID")
    top_k: int = Field(default=5, ge=1, le=20)
    max_iter: int = Field(default=3, ge=1, le=10)
    relevance_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class ReflectionTestResponse(BaseModel):
    iterations: int
    converged: bool
    original_query: str
    refined_queries: list[str]
    final_doc_count: int
    initial_doc_count: int
    history: list[dict[str, Any]]
    elapsed_ms: float


class ReflectionStatsResponse(BaseModel):
    book_id: int | None
    total_calls: int
    avg_iterations: float
    convergence_rate: float
    avg_threshold_filtered: float


@rag_router.post("/reflection_test", response_model=ReflectionTestResponse)
async def test_reflection(
    req: ReflectionTestRequest,
    session: AsyncSession = Depends(get_session),
):
    """反射スクリーニングをテスト実行"""
    reflective = ReflectiveRAGService(
        rag_service=rag_service,
        top_k=req.top_k,
        max_iter=req.max_iter,
        relevance_threshold=req.relevance_threshold,
    )

    result = await reflective.retrieve_with_reflection(
        session,
        query=req.query,
        book_id=req.book_id,
        top_k=req.top_k,
        max_iter=req.max_iter,
        relevance_threshold=req.relevance_threshold,
    )

    return ReflectionTestResponse(
        iterations=result.iterations,
        converged=result.converged,
        original_query=result.original_query,
        refined_queries=result.refined_queries,
        final_doc_count=result.final_doc_count,
        initial_doc_count=result.initial_doc_count,
        history=result.history,
        elapsed_ms=result.elapsed_ms,
    )


@rag_router.get("/reflection_stats", response_model=ReflectionStatsResponse)
async def get_reflection_stats(
    book_id: int | None = Query(None, description="書籍ID（指定時はその書籍のみ）"),
):
    """反射スクリーニングの統計を取得（DB履歴から集計）"""
    # TODO: 実際のDBクエリ実装
    # ここではモックデータを返す
    return ReflectionStatsResponse(
        book_id=book_id,
        total_calls=0,
        avg_iterations=0.0,
        convergence_rate=0.0,
        avg_threshold_filtered=0.0,
    )


__all__ = ["router", "rag_router"]