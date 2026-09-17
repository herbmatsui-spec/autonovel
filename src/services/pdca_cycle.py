"""Closed-loop PDCA Runner (Phase 4 / Part 4).

Orchestrates iterative evaluation, writing directive generation, chapter regeneration,
and re-audit until reaching the target score or detecting convergence.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List

from src.models.patch_pdca import ParagraphTarget, PatchRewriteResult
from src.services.audit_aggregator import AuditAggregator
from src.services.audit.targeted_diagnostic import TargetedDiagnostic
from src.services.book_score_mapping import UnifiedBookScoreBridge
from src.services.prose.paragraph_indexer import ParagraphIndexer
from src.services.prose.patch_merger import PatchMerger
from src.services.pdca_directive import (
    PDCACycleResult,
    WritingDirective,
)
from src.agents.writing.paragraph_patch_agent import ParagraphPatchAgent
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
        # New dependencies for paragraph patching
        indexer: ParagraphIndexer | None = None,
        diagnostic: TargetedDiagnostic | None = None,
        patch_agent: ParagraphPatchAgent | None = None,
        patch_merger: PatchMerger | None = None,
    ) -> None:
        self.aggregator = aggregator
        self.writer = writer  # Kept for compatibility, but not used in new loop
        self.bridge = bridge or UnifiedBookScoreBridge()
        self.target_score = target_score
        self.max_cycles = max(1, max_cycles)
        self.min_improvement_delta = min_improvement_delta
        self.event_bus = event_bus
        self.pdca_history_repo = pdca_history_repo
        # New dependencies
        self.indexer = indexer or ParagraphIndexer()
        self.diagnostic = diagnostic or TargetedDiagnostic()
        self.patch_agent = patch_agent or ParagraphPatchAgent()
        self.patch_merger = patch_merger or PatchMerger()

    async def run_pdca_cycle(
        self,
        initial_context: dict[str, Any],
        genre: str = "general",
        phase: str = "draft",
    ) -> tuple[str, PDCACycleResult]:
        """Execute closed-loop PDCA regeneration using paragraph patching.

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

        # 2. PDCA Loop with paragraph patching
        for cycle in range(1, self.max_cycles + 1):
            if converged:
                logger.info("PDCA converged: current score %.1f >= target %.1f", current_score, self.target_score)
                break

            # A. Identify weak paragraphs from the latest audit
            latest_audit = self.aggregator.aggregate(genre=genre)
            target_paras: List[ParagraphTarget] = self.diagnostic.identify_weak_paragraphs(latest_audit)
            if not target_paras:
                logger.info("No weak paragraphs identified in cycle %d, stopping loop", cycle)
                break

            # B. Index the current draft to get paragraphs and context
            indexed_paras = self.indexer.index_paragraphs(current_draft)
            # indexed_paras is a list of dicts: [{'index': i, 'text': para}, ...]

            # C. For each target paragraph, rewrite it with context
            patches: List[PatchRewriteResult] = []
            for target in target_paras:
                idx = target.index
                # Get context: previous and next paragraphs
                prev_para = indexed_paras[idx - 1]['text'] if idx > 0 else ""
                next_para = indexed_paras[idx + 1]['text'] if idx < len(indexed_paras) - 1 else ""
                context = {
                    'prev_paragraph': prev_para,
                    'next_paragraph': next_para,
                    # We could also pass the directive and issue_category if needed by the agent
                    'directive': target.directive,
                    'issue_category': target.issue_category,
                }
                # Rewrite the paragraph
                patch_result = await self.patch_agent.rewrite_paragraph(target, context)
                patches.append(patch_result)

            # D. Merge the patches into the draft
            new_draft = self.patch_merger.merge_patches(current_draft, patches)
            if not new_draft or len(new_draft.strip()) == 0:
                logger.warning("Patch merge returned empty draft during cycle %d, stopping loop", cycle)
                break

            current_draft = new_draft
            ctx["draft_text"] = current_draft

            # E. Re-audit the new draft
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
                "directives_count": len(target_paras),  # Number of paragraphs patched
                "delta": delta,
            })

            # Real-time event broadcast for live score monitor
            try:
                from src.backend.websocket.pipeline_hub import pipeline_event_hub
                from src.backend.schemas.pipeline_events import PipelineEvent
                await pipeline_event_hub.broadcast(
                    PipelineEvent(
                        event_type="score_updated",
                        book_id=ctx.get("book_id", 0) or 0,
                        task_id=str(ctx.get("task_id", "") or ctx.get("chapter_number", "")),
                        payload={
                            "cycle": cycle,
                            "score": current_score,
                            "delta": delta,
                            "scores_by_specialist": dict(re_audit.by_specialist),
                            "actionable_diffs": [
                                {
                                    "location": d.location,
                                    "original_quote": d.original_quote,
                                    "improved_suggestion": d.improved_suggestion,
                                    "rationale": d.rationale,
                                } for d in getattr(re_audit, "actionable_diffs", [])
                            ],
                        }
                    )
                )
            except Exception:
                pass

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
            directives_applied=all_directives,  # Note: we are not collecting WritingDirective objects anymore
            history=history,
            converged=converged,
        )

        await self._save_snapshot(result, ctx)
        await self._publish_pdca_finished(result, ctx)
        return best_draft, result

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
        """Publish PDCA outcome to event_bus and PipelineEventHub."""
        if self.event_bus:
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

        try:
            from src.backend.websocket.pipeline_hub import pipeline_event_hub
            from src.backend.schemas.pipeline_events import PipelineEvent
            await pipeline_event_hub.broadcast(
                PipelineEvent(
                    event_type="pdca_cycle",
                    book_id=ctx.get("book_id", 0) or 0,
                    task_id=str(ctx.get("task_id", "") or ctx.get("chapter_number", "")),
                    payload={
                        "initial_score": result.initial_score,
                        "final_score": result.final_score,
                        "score_delta": result.score_delta,
                        "improved_percentage": result.improved_percentage,
                        "cycles_run": result.cycle_number,
                        "converged": result.converged,
                        "history": result.history,
                    }
                )
            )
        except Exception:
            pass


__all__ = ["ClosedLoopPDCARunner"]
