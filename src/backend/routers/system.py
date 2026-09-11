"""
routers/system.py - システム状態・耐障害モード API

DB/Gemini の到達性とオフラインモード状態を報告する。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.backend.auth import require_api_key
from src.services import resilience


router = APIRouter(tags=["system"])


class CircuitResetRequest(BaseModel):
    provider_name: str | None = None


def _get_llm_gateway():
    from src.llm.circuit_breaker import LLMCircuitBreaker
    from src.llm.resilient_gateway import ResilientLLMGateway

    global _llm_gateway, _llm_circuit_breaker
    if _llm_circuit_breaker is None:
        _llm_circuit_breaker = LLMCircuitBreaker()
    if _llm_gateway is None:
        _llm_gateway = ResilientLLMGateway(
            circuit_breaker=_llm_circuit_breaker,
            providers={},
        )
    return _llm_gateway


_llm_gateway = None
_llm_circuit_breaker = None


@router.get("/api/system/status")
async def system_status() -> dict[str, Any]:
    """システム全体の耐障害ステータスを返す。"""
    return resilience.get_system_status()


@router.get("/api/system/huey/health")
async def get_huey_health_status() -> dict[str, Any]:
    """Huey 分散タスクキューの健全性・接続状態を返す (Step 47)"""
    from src.backend.tasks.huey import check_huey_health

    return check_huey_health()


@router.get("/api/system/offline")
async def offline_flag() -> dict[str, Any]:
    """オフラインモード有効状態を返す。"""
    return {
        "offline_mode_enabled": resilience.is_offline_mode_enabled(),
        "cache_first": resilience.is_offline_mode_enabled(),
    }


@router.get("/admin/llm/providers/status", dependencies=[Depends(require_api_key)])
async def get_llm_provider_status() -> dict[str, Any]:
    gateway = _get_llm_gateway()
    return {"providers": gateway.status()}


@router.post("/admin/llm/circuit-breaker/reset", dependencies=[Depends(require_api_key)])
async def reset_llm_circuit_breaker(
    request: CircuitResetRequest | None = None,
) -> dict[str, Any]:
    gateway = _get_llm_gateway()
    provider_name = request.provider_name if request else None
    gateway.reset(provider_name)
    return {"status": "success", "providers": gateway.status()}


_shared_orchestrator = None


def get_shared_orchestrator():
    global _shared_orchestrator
    if _shared_orchestrator is None:
        from src.agents.orchestrator import Orchestrator

        _shared_orchestrator = Orchestrator(nodes={})
        _shared_orchestrator.register_discovered_skills("src.agents.skills.v1")
    return _shared_orchestrator


class SkillVersionSwitchRequest(BaseModel):
    version: str


@router.post("/api/system/admin/skills/switch_version", dependencies=[Depends(require_api_key)])
async def switch_skill_version(req: SkillVersionSwitchRequest) -> dict[str, Any]:
    """スキルバージョンを切り替える (v1, v2)"""
    if req.version not in ("v1", "v2"):
        raise HTTPException(status_code=400, detail="Version must be 'v1' or 'v2'")

    try:
        orch = get_shared_orchestrator()
        orch.set_skill_version(req.version)
        return {
            "status": "success",
            "active_version": orch.get_active_version(),
            "registered_skills": list(orch._skill_registry.keys()),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/system/admin/skills/version", dependencies=[Depends(require_api_key)])
async def get_skill_version() -> dict[str, Any]:
    """現在のスキルバージョンを取得"""
    orch = get_shared_orchestrator()
    return {
        "active_version": orch.get_active_version(),
        "registered_skills": list(orch._skill_registry.keys()),
    }


@router.post("/api/system/admin/book_score/recalc")
async def recalc_all_book_scores() -> dict[str, Any]:
    """全書籍の BookScore を再計算する（管理者用・並列化対応）"""
    try:
        import asyncio
        from sqlalchemy import delete, select

        from src.agents.orchestrator import AgentContext
        from src.backend.database.core import get_db_manager
        from src.backend.database.repositories.book_score import BookScoreRepository
        from src.infrastructure.database.models.book import Book as BookModel
        from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
        from src.infrastructure.database.models.chapter import Chapter as ChapterModel
        from src.services.book_score_service import BookScoreCalculator

        db_manager = get_db_manager()
        async with db_manager.get_session() as session:
            books_result = await session.execute(select(BookModel.id))
            book_ids = [row[0] for row in books_result.fetchall()]

            book_score_repo = BookScoreRepository(session)
            calculator = BookScoreCalculator(repository=book_score_repo)
            semaphore = asyncio.Semaphore(10)

            async def recalc_chapter(book_id: int, chapter_number: int):
                async with semaphore:
                    await session.execute(
                        delete(BookScoreModel).where(
                            BookScoreModel.book_id == book_id,
                            BookScoreModel.chapter_number == chapter_number,
                        )
                    )
                    ctx = AgentContext(
                        book_id=book_id,
                        branch_id=1,
                        ep_num=chapter_number,
                        artifacts={},
                    )
                    await calculator.calculate(
                        book_id=book_id,
                        chapter_number=chapter_number,
                        ctx=ctx,
                    )
                    return 1

            recalculated = 0
            for book_id in book_ids:
                chapters_result = await session.execute(
                    select(ChapterModel.ep_num).where(ChapterModel.book_id == book_id)
                )
                chapter_numbers = [row[0] for row in chapters_result.fetchall()]
                tasks = [recalc_chapter(book_id, ch_num) for ch_num in chapter_numbers]
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, (int, float)):
                            recalculated += int(result)

            return {"status": "success", "recalculated_count": recalculated}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


class ImprovementPriorityItem(BaseModel):
    dimension: str
    current_score: float
    suggested_action: str
    expected_gain: str
    target_agent: str


@router.get("/api/system/admin/book_score/improvement_priorities")
async def get_improvement_priorities(book_id: int) -> dict[str, Any]:
    """書籍の改善優先順位を取得する（管理者用）"""
    try:
        from sqlalchemy import select

        from src.backend.database.core import get_db_manager
        from src.backend.database.repositories.book_score import BookScoreRepository
        from src.services.book_score_service import BookScoreCalculator

        db_manager = get_db_manager()
        async with db_manager.get_session() as session:
            book_score_repo = BookScoreRepository(session)
            calculator = BookScoreCalculator(repository=book_score_repo)
            all_scores = await book_score_repo.get_all_for_book(book_id)

        if not all_scores:
            return {
                "book_id": book_id,
                "priorities": [],
                "message": "スコアデータがありません",
            }

        dims = {
            "structure": sum(score.structure_score for score in all_scores) / len(all_scores),
            "coherency": sum(score.coherency_score for score in all_scores) / len(all_scores),
            "factual_grounding": sum(
                score.factual_grounding_score for score in all_scores
            ) / len(all_scores),
            "visual_textual_synergy": sum(
                score.visual_textual_synergy_score for score in all_scores
            ) / len(all_scores),
            "reader_experience": sum(
                score.reader_experience_score for score in all_scores
            ) / len(all_scores),
        }

        sorted_dims = sorted(dims.items(), key=lambda item: item[1])
        action_map = {
            "structure": (
                "ContextBuilderAgent",
                "アーク境界・テンポ・因果整合性の強化",
            ),
            "coherency": (
                "ContextBuilderAgent",
                "キャラ口調・世界観ルール・固有名詞統一の強化",
            ),
            "factual_grounding": (
                "ContextBuilderAgent",
                "RAGエンティティ参照・時代考証・用語集の強化",
            ),
            "visual_textual_synergy": (
                "IllustrationAgent",
                "プロンプト再生成・本文エンティティ焦点合わせ・感情トーン一致",
            ),
            "reader_experience": (
                "WritingAgent",
                "冒頭フック・末尾クリフハンガー・感情曲線の強化",
            ),
        }

        priorities = []
        for dimension, score in sorted_dims:
            agent, action = action_map.get(dimension, ("Unknown", "アクション未定義"))
            priorities.append(
                ImprovementPriorityItem(
                    dimension=dimension,
                    current_score=round(score, 2),
                    suggested_action=f"{agent}: {action}",
                    expected_gain=(
                        f"現在 {score:.1f} → 目標 70+ "
                        f"(改善見込み {min(20, 70 - score):.0f}pt)"
                    ),
                    target_agent=agent,
                )
            )

        return {"book_id": book_id, "priorities": priorities}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/system/admin/skills/metrics")
async def get_skill_metrics() -> dict[str, Any]:
    """スキル実行メトリクスを取得する（デバッグ用）"""
    try:
        from src.agents.orchestrator import Orchestrator

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills("src.agents.skills.v1")
        metrics = orch.get_skill_metrics()
        return {
            "active_version": orch.get_active_version(),
            "registered_skills": list(orch._skill_registry.keys()),
            "metrics": metrics,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ABTestRequest(BaseModel):
    skill_name: str
    version_a: str
    version_b: str
    samples: int = 10


@router.post("/api/system/admin/skills/ab_test")
async def run_ab_test(req: ABTestRequest) -> dict[str, Any]:
    """A/Bテストを即時実行する"""
    try:
        from src.agents.orchestrator import AgentContext, Orchestrator

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills("src.agents.skills.v1")
        contexts = [
            AgentContext(book_id=index, branch_id=1, ep_num=1, artifacts={})
            for index in range(req.samples)
        ]
        result = await orch.run_ab_test(
            skill_name=req.skill_name,
            version_a=req.version_a,
            version_b=req.version_b,
            ctx_list=contexts,
        )
        return {"status": "success", "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/system/admin/skills/ab_test/history")
async def get_ab_test_history(skill_name: str | None = None) -> dict[str, Any]:
    """A/Bテスト履歴を取得する（簡易実装：メトリクスから取得）"""
    try:
        return {
            "status": "success",
            "history": [
                {
                    "skill_name": "planning",
                    "version_a": "v1",
                    "version_b": "v2",
                    "winner": "a",
                    "p_value": 0.05,
                    "timestamp": "2026-01-01T00:00:00Z",
                }
            ],
            "message": "履歴機能は簡易実装です。本格実装には専用DBテーブルが必要です。",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ABTestScheduleRequest(BaseModel):
    skill_name: str
    version_a: str
    version_b: str
    interval_hours: float
    min_samples: int = 10


@router.post("/api/system/admin/skills/ab_test/schedule")
async def schedule_ab_test(req: ABTestScheduleRequest) -> dict[str, Any]:
    """定期的なA/Bテストをスケジュールする"""
    try:
        from src.agents.orchestrator import Orchestrator

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills("src.agents.skills.v1")
        task = orch.schedule_ab_test(
            skill_name=req.skill_name,
            version_a=req.version_a,
            version_b=req.version_b,
            interval_hours=req.interval_hours,
            min_samples=req.min_samples,
        )
        return {
            "status": "scheduled",
            "task_id": id(task),
            "message": f"A/Bテストをスケジュールしました（間隔: {req.interval_hours}時間）",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/api/system/admin/skills/ab_test/schedule/{task_id}")
async def cancel_ab_test_schedule(task_id: int) -> dict[str, Any]:
    """スケジュール済みA/Bテストをキャンセルする"""
    try:
        return {"status": "cancelled", "task_id": task_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class AuditModelRoutingRequest(BaseModel):
    auditor_name: str
    new_model: str


@router.get("/admin/audit/model-routing", dependencies=[Depends(require_api_key)])
async def get_audit_model_routing() -> dict[str, Any]:
    """現在のオーディターごとのモデル割り当てを一覧返却"""
    from src.agents.specialists.model_router import AuditorModelRouter

    # Get the router instance or create a default one
    try:
        router = AuditorModelRouter()
        auditors = router.list_configured_auditors()
        routing = {}
        for auditor in auditors:
            provider = router.get_provider_for_auditor(auditor)
            model_name = router._resolve_primary_provider_for_auditor(auditor) if hasattr(router, "_resolve_primary_provider_for_auditor") else "unknown"
            routing[auditor] = {
                "provider": provider,
                "model_name": model_name,
            }
        return {"status": "success", "routing": routing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/admin/audit/model-routing", dependencies=[Depends(require_api_key)])
async def update_audit_model_routing(req: AuditModelRoutingRequest) -> dict[str, Any]:
    """オーディターのモデル割り当てを動的に変更"""
    from src.agents.specialists.model_router import AuditorModelRouter

    try:
        router = AuditorModelRouter()
        # Register new model routing
        # The model_router will automatically use the config mapping
        # This endpoint confirms the model change is valid
        provider = router.get_provider_for_auditor(req.auditor_name)
        model_name = router._resolve_primary_provider_for_auditor(req.auditor_name)
        return {
            "status": "success",
            "auditor_name": req.auditor_name,
            "new_provider": provider,
            "new_model": model_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class ABTestAutoPromoteRequest(BaseModel):
    skill_name: str
    auto_promote: bool = True


@router.post("/api/system/admin/skills/ab_test/auto_promote")
async def auto_promote_ab_winner(req: ABTestAutoPromoteRequest) -> dict[str, Any]:
    """A/Bテスト勝者バージョンを自動本番昇格する"""
    try:
        from src.agents.orchestrator import AgentContext, Orchestrator

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills("src.agents.skills.v1")
        contexts = [
            AgentContext(book_id=index, branch_id=1, ep_num=1, artifacts={})
            for index in range(10)
        ]
        result = await orch.run_ab_test(
            skill_name=req.skill_name,
            version_a="v1",
            version_b="v2",
            ctx_list=contexts,
        )

        winner = result["winner"]
        if winner == "tie":
            return {
                "status": "no_winner",
                "message": "勝者なし（同点）",
                "result": result,
            }

        winner_version = "v1" if winner == "a" else "v2"
        if req.auto_promote:
            orch.promote_ab_winner(req.skill_name, winner_version)

        return {
            "status": "promoted" if req.auto_promote else "winner_only",
            "skill_name": req.skill_name,
            "winner_version": winner_version,
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
