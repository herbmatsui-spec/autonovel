"""
planning_service.py - PlanningService: 企画・プロット生成を担当するドメインサービス。

UltimateHegemonyEngine から分離したサービス。
ワークフロー (FullAutoWorkflow, PlanGenerationWorkflow 等) は PlanningService を
依存対象にし、EngineFacade 経由でインジェクトされる。

責任:
- create_hegemony_plan: 企画生成 (WorldBibleGenerator へ委譲)
- audit_bible_completeness: 整合性監査 (bible_generator.auditor へ委譲)
- predict_book_score_from_outline: 企画アウトラインから BookScore 予測
"""

from __future__ import annotations

from typing import Any


class PlanningService:
    """覇権小説の企画・プロット生成を担当するサービス。"""

    def __init__(
        self,
        bible_generator: Any,  # WorldBibleGenerator (engine.planner として注入される実体)
        repo: Any,  # DataRepository
        pm: Any,  # PromptManager
        ctx_mgr: Any,  # ContextManager
        reporter_factory: Any,  # StatusReporter 作成用 Callable
        book_score_calculator: Any = None,  # BookScoreCalculator
    ) -> None:
        self.bible_generator = bible_generator
        self.repo = repo
        self.pm = pm
        self.ctx_mgr = ctx_mgr
        self.reporter_factory = reporter_factory
        self.book_score_calculator = book_score_calculator

    async def create_hegemony_plan(
        self,
        genre: str = None,
        keywords: str = None,
        style_key: str = None,
        concept: str = None,
        title: str = "",
        cheat_scale: int = 4,
        growth_curve: str = "最初からカンスト(無双)",
        system_assist: int = 70,
        cost_severity: int = 2,
        target_eps: int = 10,
        initial_plot_limit: int = 3,
        reporter: Any | None = None,
    ) -> tuple[int, Any]:
        """覇権企画を生成し、book_id と bible を返す (WorldBibleGenerator へ委譲)。"""
        return await self.bible_generator.create_hegemony_plan(
            genre=genre,
            keywords=keywords,
            style_key=style_key,
            concept=concept,
            title=title,
            cheat_scale=cheat_scale,
            growth_curve=growth_curve,
            system_assist=system_assist,
            cost_severity=cost_severity,
            target_eps=target_eps,
            initial_plot_limit=initial_plot_limit,
            reporter=reporter,
        )

    async def audit_bible_completeness(
        self,
        book_id: int,
        reporter: Any = None,
    ) -> bool:
        """Bible の整合性を監査する (bible_generator.auditor へ委譲)。"""
        auditor = getattr(self.bible_generator, "auditor", None)
        if auditor is None or not hasattr(auditor, "audit_bible_completeness"):
            return True
        return await auditor.audit_bible_completeness(book_id, reporter=reporter)

    async def predict_book_score_from_outline(
        self,
        arcs: list[Any],
        genre: str = "",
        target_eps: int = 10,
    ) -> dict[str, float]:
        """企画アウトラインから BookScore を予測する（構造スコア・読者体験スコア中心）。
        
        単一アーク構成の評価。3案比較時はこのメソッドを各案に対して呼び出す。
        """
        if self.book_score_calculator is None:
            return {"overall_score": 0.0, "structure_score": 0.0, "reader_experience_score": 0.0}

        # 擬似的な AgentContext を作成して計算
        from src.agents.orchestrator import AgentContext
        ctx = AgentContext(book_id=0, branch_id=1, ep_num=1, artifacts={"arcs": arcs})

        # 簡易実装: 構造スコアはアークの論理的流れから、読者体験は冒頭フックから推定
        structure = await self._estimate_structure_score(arcs, target_eps)
        reader_exp = await self._estimate_reader_experience(arcs)

        # 他次元はデフォルト値
        weights = self.book_score_calculator._get_weights(genre, "planning")
        overall = (
            structure * weights.get("structure", 25) / 100
            + 50.0 * weights.get("coherency", 25) / 100
            + 50.0 * weights.get("factual_grounding", 20) / 100
            + 50.0 * weights.get("visual_textual_synergy", 15) / 100
            + reader_exp * weights.get("reader_experience", 15) / 100
        )

        return {
            "overall_score": round(overall, 2),
            "structure_score": round(structure, 2),
            "coherency_score": 50.0,
            "factual_grounding_score": 50.0,
            "visual_textual_synergy_score": 50.0,
            "reader_experience_score": round(reader_exp, 2),
        }

    async def predict_book_score_for_proposals(
        self,
        proposals: list[list[Any]],  # 各案のアークリスト
        genre: str = "",
        target_eps: int = 10,
    ) -> list[dict[str, Any]]:
        """3案企画ガチャの各案について BookScore を予測・比較・推奨案を返す"""
        results = []
        for i, arcs in enumerate(proposals):
            score_dict = await self.predict_book_score_from_outline(arcs, genre, target_eps)
            score_dict["proposal_index"] = i
            score_dict["proposal_name"] = f"案{i+1}"
            results.append(score_dict)
        
        # 総合スコアでソート（降順）
        results.sort(key=lambda x: x["overall_score"], reverse=True)
        
        # 推奨フラグ付与
        for i, r in enumerate(results):
            r["recommended"] = (i == 0)
            r["rank"] = i + 1
        
        return results

    async def _estimate_structure_score(self, arcs: list[Any], target_eps: int) -> float:
        """アーク構成から構造スコアを推定 (0-100)"""
        if not arcs:
            return 30.0
        # アークの数、話数配分、クライマックス位置などから簡易評価
        num_arcs = len(arcs)
        ideal_arcs = max(1, target_eps // 8)  # 8話ごとに1アークが理想
        arc_balance = min(100.0, (ideal_arcs / max(1, num_arcs)) * 100)
        # クライマックスが適切な位置にあるかチェック
        climax_score = 70.0
        for arc in arcs:
            end_ep = getattr(arc, "end_ep", None) or (arc.get("end_ep") if isinstance(arc, dict) else None)
            if end_ep and end_ep in [target_eps // 2, target_eps * 3 // 4, target_eps]:
                climax_score = 90.0
                break
        return (arc_balance + climax_score) / 2

    async def _estimate_reader_experience(self, arcs: list[Any]) -> float:
        """アーク構成から読者体験スコアを推定 (0-100)"""
        if not arcs:
            return 40.0
        # 第1話のフック、最終話の決着感などから推定
        first_arc = arcs[0]
        last_arc = arcs[-1]
        hook_score = 60.0
        if isinstance(first_arc, dict) and first_arc.get("start_ep", 1) == 1:
            hook_score = 80.0
        elif hasattr(first_arc, "start_ep") and first_arc.start_ep == 1:
            hook_score = 80.0
        payoff_score = 70.0
        if isinstance(last_arc, dict) and last_arc.get("end_ep", 0) > 0:
            payoff_score = 85.0
        elif hasattr(last_arc, "end_ep") and last_arc.end_ep > 0:
            payoff_score = 85.0
        return (hook_score + payoff_score) / 2
