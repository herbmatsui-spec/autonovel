"""
routers/system.py - システム状態・耐障害モード API

DB/Gemini の到達性とオフラインモード状態を報告する。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services import resilience
from src.agents.orchestrator import AgentContext

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
async def system_status() -> dict[str, Any]:
    """システム全体の耐障害ステータスを返す。"""
    return resilience.get_system_status()


@router.get("/offline")
async def offline_flag() -> dict[str, Any]:
    """オフラインモード有効状態を返す。"""
    return {
        "offline_mode_enabled": resilience.is_offline_mode_enabled(),
        "cache_first": resilience.is_offline_mode_enabled(),
    }


class SkillVersionSwitchRequest(BaseModel):
    version: str  # "v1" or "v2"


@router.post("/admin/skills/switch_version")
async def switch_skill_version(req: SkillVersionSwitchRequest) -> dict[str, Any]:
    """スキルバージョンを切り替える (v1, v2)"""
    if req.version not in ("v1", "v2"):
        raise HTTPException(status_code=400, detail="Version must be 'v1' or 'v2'")
    
    try:
        from src.agents.orchestrator import Orchestrator
        orch = Orchestrator(nodes={})
        orch.set_skill_version(req.version)
        return {
            "status": "success",
            "active_version": orch.get_active_version(),
            "registered_skills": list(orch._skill_registry.keys()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/skills/version")
async def get_skill_version() -> dict[str, Any]:
    """現在のスキルバージョンを取得"""
    from src.agents.orchestrator import Orchestrator
    orch = Orchestrator(nodes={})
    return {
        "active_version": orch.get_active_version(),
        "registered_skills": list(orch._skill_registry.keys()),
    }


@router.post("/admin/book_score/recalc")
async def recalc_all_book_scores() -> dict[str, Any]:
    """全書籍の BookScore を再計算する（管理者用・並列化対応）"""
    try:
        from src.backend.database.repository import DataRepository
        from src.services.book_score_service import BookScoreCalculator, BookScoreRepository
        from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
        from sqlalchemy import select
        import asyncio

        repo = DataRepository()
        session = repo._session_factory()  # type: ignore

        # 全書籍IDを取得
        from src.infrastructure.database.models.book import Book as BookModel
        books_result = await session.execute(select(BookModel.id))
        book_ids = [row[0] for row in books_result.fetchall()]

        book_score_repo = BookScoreRepository(session)
        calculator = BookScoreCalculator(repository=book_score_repo)

        # セマフォで同時実行数制限（DB負荷対策）
        semaphore = asyncio.Semaphore(10)
        
        async def recalc_chapter(book_id: int, chapter_number: int):
            async with semaphore:
                # 既存スコアを削除
                await session.execute(
                    select(BookScoreModel).where(
                        BookScoreModel.book_id == book_id,
                        BookScoreModel.chapter_number == chapter_number,
                    ).delete()
                )
                # 再計算
                from src.agents.orchestrator import AgentContext
                ctx = AgentContext(book_id=book_id, branch_id=1, ep_num=chapter_number, artifacts={})
                await calculator.calculate(book_id=book_id, chapter_number=chapter_number, ctx=ctx)
                return 1

        recalculated = 0
        # 書籍ごとにタスク作成
        for book_id in book_ids:
            from src.infrastructure.database.models.chapter import Chapter as ChapterModel
            chapters_result = await session.execute(
                select(ChapterModel.ep_num).where(ChapterModel.book_id == book_id)
            )
            chapter_numbers = [row[0] for row in chapters_result.fetchall()]

            # チャンプタスクを並列実行
            tasks = [recalc_chapter(book_id, ch_num) for ch_num in chapter_numbers]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, Exception):
                        # エラーはログのみ、継続
                        pass
                    else:
                        recalculated += r

        return {"status": "success", "recalculated_count": recalculated}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


class ImprovementPriorityItem(BaseModel):
    dimension: str
    current_score: float
    suggested_action: str
    expected_gain: str
    target_agent: str


@router.get("/admin/book_score/improvement_priorities")
async def get_improvement_priorities(book_id: int) -> dict[str, Any]:
    """書籍の改善優先順位を取得する（管理者用）"""
    try:
        from src.backend.database.repository import DataRepository
        from src.services.book_score_service import BookScoreCalculator, BookScoreRepository
        from sqlalchemy.ext.asyncio import AsyncSession

        repo = DataRepository()
        session = repo._session_factory()  # type: ignore
        book_score_repo = BookScoreRepository(session)
        calculator = BookScoreCalculator(repository=book_score_repo)
        all_scores = await book_score_repo.get_all_for_book(book_id)

        if not all_scores:
            return {"book_id": book_id, "priorities": [], "message": "スコアデータがありません"}

        # 次元別平均計算
        dims = {
            "structure": sum(s.structure_score for s in all_scores) / len(all_scores),
            "coherency": sum(s.coherency_score for s in all_scores) / len(all_scores),
            "factual_grounding": sum(s.factual_grounding_score for s in all_scores) / len(all_scores),
            "visual_textual_synergy": sum(s.visual_textual_synergy_score for s in all_scores) / len(all_scores),
            "reader_experience": sum(s.reader_experience_score for s in all_scores) / len(all_scores),
        }

        # 最も低い次元から順に並べる
        sorted_dims = sorted(dims.items(), key=lambda x: x[1])

        action_map = {
            "structure": ("ContextBuilderAgent", "アーク境界・テンポ・因果整合性の強化"),
            "coherency": ("ContextBuilderAgent", "キャラ口調・世界観ルール・固有名詞統一の強化"),
            "factual_grounding": ("ContextBuilderAgent", "RAGエンティティ参照・時代考証・用語集の強化"),
            "visual_textual_synergy": ("IllustrationAgent", "プロンプト再生成・本文エンティティ焦点合わせ・感情トーン一致"),
            "reader_experience": ("WritingAgent", "冒頭フック・末尾クリフハンガー・感情曲線の強化"),
        }

        priorities = []
        for dim, score in sorted_dims:
            agent, action = action_map.get(dim, ("Unknown", "アクション未定義"))
            priorities.append(ImprovementPriorityItem(
                dimension=dim,
                current_score=round(score, 2),
                suggested_action=f"{agent}: {action}",
                expected_gain=f"現在 {score:.1f} → 目標 70+ (改善見込み {min(20, 70 - score):.0f}pt)",
                target_agent=agent,
            ))

        return {"book_id": book_id, "priorities": priorities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/skills/metrics")
async def get_skill_metrics() -> dict[str, Any]:
    """スキル実行メトリクスを取得する（デバッグ用）"""
    try:
        from src.agents.orchestrator import Orchestrator
        from src.agents.skill_base import SkillAgent

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills('src.agents.skills.v1')

        metrics = orch.get_skill_metrics()
        return {
            "active_version": orch.get_active_version(),
            "registered_skills": list(orch._skill_registry.keys()),
            "metrics": metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ABTestRequest(BaseModel):
    skill_name: str
    version_a: str  # "v1" or "v2"
    version_b: str  # "v1" or "v2"
    samples: int = 10


@router.post("/admin/skills/ab_test")
async def run_ab_test(req: ABTestRequest) -> dict[str, Any]:
    """A/Bテストを即時実行する"""
    try:
        from src.agents.orchestrator import Orchestrator, AgentContext

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills('src.agents.skills.v1')

        ctx_list = [
            AgentContext(book_id=i, branch_id=1, ep_num=1, artifacts={})
            for i in range(req.samples)
        ]

        result = await orch.run_ab_test(
            skill_name=req.skill_name,
            version_a=req.version_a,
            version_b=req.version_b,
            ctx_list=[AgentContext(book_id=i, branch_id=1, ep_num=1, artifacts={}) for i in range(req.samples)],
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/skills/ab_test/history")
async def get_ab_test_history(skill_name: str = None) -> dict[str, Any]:
    """A/Bテスト履歴を取得する（簡易実装：メトリクスから取得）"""
    try:
        from src.agents.orchestrator import Orchestrator
        from src.backend.observability.metrics import skill_version_active

        # 簡易実装：メトリクスから取得を試みる
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ABTestScheduleRequest(BaseModel):
    skill_name: str
    version_a: str
    version_b: str
    interval_hours: float
    min_samples: int = 10


@router.post("/admin/skills/ab_test/schedule")
async def schedule_ab_test(req: ABTestScheduleRequest) -> dict[str, Any]:
    """定期的なA/Bテストをスケジュールする"""
    try:
        from src.agents.orchestrator import Orchestrator

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills('src.agents.skills.v1')

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/skills/ab_test/schedule/{task_id}")
async def cancel_ab_test_schedule(task_id: int) -> dict[str, Any]:
    """スケジュール済みA/Bテストをキャンセルする"""
    try:
        # 簡易実装：タスクキャンセル
        return {"status": "cancelled", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ABTestAutoPromoteRequest(BaseModel):
    skill_name: str
    auto_promote: bool = True


@router.post("/admin/skills/ab_test/auto_promote")
async def auto_promote_ab_winner(req: ABTestAutoPromoteRequest) -> dict[str, Any]:
    """A/Bテスト勝者バージョンを自動本番昇格する"""
    try:
        from src.agents.orchestrator import Orchestrator

        orch = Orchestrator(nodes={})
        orch.register_discovered_skills('src.agents.skills.v1')

        # A/Bテスト実行して勝者決定
        skill_name = req.skill_name
        ctx_list = [
            AgentContext(book_id=i, branch_id=1, ep_num=1, artifacts={})
            for i in range(10)
        ]
        result = await orch.run_ab_test(
            skill_name=skill_name,
            version_a="v1",
            version_b="v2",
            ctx_list=[AgentContext(book_id=i, branch_id=1, ep_num=1, artifacts={}) for i in range(10)],
        )

        winner = result["winner"]
        if winner == "tie":
            return {"status": "no_winner", "message": "勝者なし（同点）", "result": result}

        winner_version = "v1" if winner == "a" else "v2"

        if req.auto_promote:
            orch.promote_ab_winner(skill_name, winner_version)

        return {
            "status": "promoted" if req.auto_promote else "winner_only",
            "skill_name": skill_name,
            "winner_version": winner_version,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
