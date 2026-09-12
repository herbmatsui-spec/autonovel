"""Closed-loop PDCA Runner (Phase 4 / Part 4).

Orchestrates iterative evaluation, writing directive generation, chapter regeneration,
and re-audit until reaching the target score or detecting convergence.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from src.services.audit_aggregator import AuditAggregator
from src.services.book_score_mapping import UnifiedBookScoreBridge
from src.services.pdca_directive import (
    PDCADirectiveGenerator,
    PDCACycleResult,
    WritingDirective,
)
from src.backend.database.models import PDCAHistorySnapshot
from src.backend.database.repositories.pdca_history import PDCAHistoryRepository

logger = logging.getLogger(__name__)


class ClosedLoopPDCARunner:
    """Manages iterative evaluation -> directive -> regeneration PDCA loops."""

    def __init__(
        self,
        aggregator: AuditAggregator,
        writer: Any | Callable[[dict[str, Any]], str],
        bridge: UnifiedBookScoreBridge | None = None,
        target_score: float = 75.0,  # Web hit standard (75.0), Commercial (85.0)
        max_cycles: int = 3,
        min_improvement_delta: float = 1.5,
        event_bus: Any | None = None,
        pdca_history_repo: PDCAHistoryRepository | None = None,
    ) -> None:
        self.aggregator = aggregator
        self.writer = writer
        self.bridge = bridge or UnifiedBookScoreBridge()
        self.target_score = target_score
        self.max_cycles = max(1, max_cycles)
        self.min_improvement_delta = min_improvement_delta
        self.event_bus = event_bus
        self.pdca_history_repo = pdca_history_repo

    async def run_pdca_cycle(
        self,
        initial_context: dict[str, Any],
        genre: str = "general",
        phase: str = "draft",
    ) -> tuple[str, PDCACycleResult]:
        """Execute closed-loop PDCA regeneration.

        Returns:
            (best_draft_text, pdca_result)
        """
        ctx = dict(initial_context)
        current_draft = str(ctx.get("draft_text", ""))
        history: list[dict[str, Any]] = []
        all_directives: list[WritingDirective] = []

        # 1. Initial audit
        await self.aggregator.run_all(ctx)
        initial_audit = self.aggregator.aggregate(genre=genre)
        initial_score = (
            initial_audit.calibrated_overall
            if initial_audit.calibrated_overall is not None
            else initial_audit.overall
        )

        current_score = initial_score
        best_draft = current_draft
        best_score = current_score

        history.append({
            "cycle": 0,
            "draft_chars": len(current_draft),
            "score": round(current_score, 2),
            "scores_by_specialist": dict(initial_audit.by_specialist),
            "calibrated_scores": dict(initial_audit.calibrated_by_specialist),
            "lowest_dimension": initial_audit.lowest_dimension(),
            "directives_count": 0,
            "delta": 0.0,
        })

        converged = current_score >= self.target_score

        # 2. PDCA Loop
        for cycle in range(1, self.max_cycles + 1):
            if converged:
                logger.info("PDCA converged: current score %.1f >= target %.1f", current_score, self.target_score)
                break

            # A. Generate targeted directives from actionable diffs and scores
            latest_audit = self.aggregator.aggregate(genre=genre)
            diffs = latest_audit.all_actionable_diffs()
            scores = (
                latest_audit.calibrated_by_specialist
                if latest_audit.calibrated_by_specialist
                else latest_audit.by_specialist
            )

            directives = PDCADirectiveGenerator.generate_directives_for_regeneration(
                scores_by_specialist=scores,
                actionable_diffs=diffs,
                target_threshold=self.target_score,
                max_directives=4,
            )
            all_directives.extend(directives)
            directive_prompt = PDCADirectiveGenerator.format_directives_for_llm_prompt(directives)

            # B. Execute rewrite / regeneration
            ctx_for_writer = dict(ctx)
            ctx_for_writer["draft_text"] = current_draft
            ctx_for_writer["pdca_directives"] = directive_prompt
            ctx_for_writer["actionable_diffs"] = diffs
            ctx_for_writer["pdca_cycle"] = cycle

            new_draft = await self._generate_rewrite(ctx_for_writer)
            if not new_draft or len(new_draft.strip()) == 0:
                logger.warning("Writer returned empty draft during cycle %d, stopping loop", cycle)
                break

            current_draft = new_draft
            ctx["draft_text"] = current_draft

            # C. Re-audit regenerated text
            await self.aggregator.run_all(ctx)
            re_audit = self.aggregator.aggregate(genre=genre)
            new_score = (
                re_audit.calibrated_overall
                if re_audit.calibrated_overall is not None
                else re_audit.overall
            )

            delta = round(new_score - current_score, 2)
            current_score = new_score

            if current_score > best_score:
                best_score = current_score
                best_draft = current_draft

            history.append({
                "cycle": cycle,
                "draft_chars": len(current_draft),
                "score": round(new_score, 2),
                "scores_by_specialist": dict(re_audit.by_specialist),
                "calibrated_scores": dict(re_audit.calibrated_by_specialist),
                "lowest_dimension": re_audit.lowest_dimension(),
                "directives_count": len(directives),
                "delta": delta,
            })

            # Check convergence or stagnation
            if current_score >= self.target_score:
                converged = True
                break
            elif cycle >= 2:
                # Check improvement percentage (15% threshold for early retry/stop)
                prev_score = current_score - delta
                if prev_score > 0:
                    improvement_pct = (delta / prev_score) * 100.0
                    if improvement_pct < 15.0:
                        logger.info(
                            "PDCA stopping early due to low improvement rate (%.1f%% < 15%%)",
                            improvement_pct,
                        )
                        break

        # Final metrics
        score_delta = round(best_score - initial_score, 2)
        improved_pct = round((score_delta / max(1.0, initial_score)) * 100.0, 2)

        result = PDCACycleResult(
            cycle_number=len(history) - 1,
            initial_score=initial_score,
            final_score=best_score,
            score_delta=score_delta,
            improved_percentage=improved_pct,
            lowest_dimension=history[-1]["lowest_dimension"] or "unknown",
            directives_applied=all_directives,
            history=history,
            converged=converged,
        )

        await self._save_snapshot(result, ctx)
        await self._publish_pdca_finished(result, ctx)
        return best_draft, result

    async def _generate_rewrite(self, ctx: dict[str, Any]) -> str:
        """Invoke writer agent or function with directives."""
        if hasattr(self.writer, "rewrite_for_dimension"):
            # WritingAgent with PDCA dimension support
            res = self.writer.rewrite_for_dimension(
                book_id=ctx.get("book_id", 1),
                branch_id=ctx.get("branch_id", 1),
                ep_num=ctx.get("chapter_number") or ctx.get("ep_num", 1),
                dimension=ctx.get("focus", "reader_experience"),
                actionable_diffs=ctx.get("actionable_diffs", []),
                reporter=ctx.get("reporter"),
            )
            if asyncio.iscoroutine(res):
                res = await res
            if isinstance(res, dict) and "rewritten_text" in res:
                return str(res["rewritten_text"])
            return str(ctx.get("draft_text", ""))
        elif hasattr(self.writer, "rewrite_with_focus"):
            # WritingAgent instance (legacy)
            res = self.writer.rewrite_with_focus(
                book_id=ctx.get("book_id", 1),
                ep_num=ctx.get("chapter_number") or ctx.get("ep_num", 1),
                focus=ctx.get("focus", "pdca_improvement"),
                params={
                    "actionable_diffs": ctx.get("actionable_diffs", []),
                    "pdca_directives": ctx.get("pdca_directives", ""),
                },
                reporter=ctx.get("reporter"),
            )
            if asyncio.iscoroutine(res):
                res = await res
            if isinstance(res, dict) and "rewritten_text" in res:
                return str(res["rewritten_text"])
            return str(ctx.get("draft_text", ""))
        elif callable(self.writer):
            res = self.writer(ctx)
            if asyncio.iscoroutine(res):
                res = await res
            return str(res)
        elif hasattr(self.writer, "generate_chapter"):
            res = self.writer.generate_chapter(ctx)
            if asyncio.iscoroutine(res):
                res = await res
            return str(res)
        elif hasattr(self.writer, "run"):
            res = self.writer.run(ctx)
            if asyncio.iscoroutine(res):
                res = await res
            return str(getattr(res, "content", res))
        return str(ctx.get("draft_text", ""))

    async def _save_snapshot(self, result: PDCACycleResult, ctx: dict[str, Any]) -> None:
        """Save the PDCA cycle result to the database."""
        if not self.pdca_history_repo:
            return

        try:
            snapshot = PDCAHistorySnapshot(
                book_id=ctx.get("book_id"),
                chapter_number=ctx.get("chapter_number") or ctx.get("ep_num"),
                cycle_number=result.cycle_number,
                initial_score=result.initial_score,
                final_score=result.final_score,
                score_delta=result.score_delta,
                improved_percentage=result.improved_percentage,
                lowest_dimension=result.lowest_dimension,
                directives=[d.to_dict() for d in result.directives_applied],
                history=result.history,
                converged=result.converged,
            )
            self.pdca_history_repo.add(snapshot)
            logger.info(
                "PDCA snapshot saved for book %s, chapter %s (cycle %d)",
                ctx.get("book_id"),
                ctx.get("chapter_number") or ctx.get("ep_num"),
                result.cycle_number,
            )
        except Exception as e:
            logger.error("Failed to save PDCA snapshot: %s", e)

    async def _publish_pdca_finished(self, result: PDCACycleResult, ctx: dict[str, Any]) -> None:
        """Publish PDCA outcome to event_bus."""
        if not self.event_bus:
            return
        try:
            from src.agents.event_bus import AgentEvent
            await self.event_bus.publish_async(
                AgentEvent(
                    agent="audit.pdca",
                    payload={
                        "event": "audit.pdca.completed",
                        "book_id": ctx.get("book_id"),
                        "chapter_number": ctx.get("chapter_number"),
                        "initial_score": result.initial_score,
                        "final_score": result.final_score,
                        "score_delta": result.score_delta,
                        "improved_percentage": result.improved_percentage,
                        "cycles_run": result.cycle_number,
                        "converged": result.converged,
                    },
                    correlation_id=str(ctx.get("correlation_id", "unknown")),
                )
            )
        except Exception:
            pass


__all__ = ["ClosedLoopPDCARunner"]
