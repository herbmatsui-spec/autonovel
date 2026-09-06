# src/agents/specialists/adapter.py
"""AuditAggregator pipeline adapter for Orchestrator integration."""
from __future__ import annotations

import logging
from typing import Any, Optional

from src.agents.orchestrator import AgentContext, AgentName, AgentResult
from src.agents.specialist_auditor_base import SpecialistAuditor
from src.agents.specialists import (
    ConsistencyAuditor,
    CreativityAuditor,
    EmotionCurveAuditor,
    FactualAuditor,
    MultimodalAuditor,
    ReaderHookAuditor,
    StructureAuditor,
    StyleAuditor,
)
from src.config.weight_variants import load_variants_from_yaml, merge_genre_phase_variants
from src.services.audit_aggregator import AuditAggregator, BookScoreResult
from src.services.experiment_allocator import ExperimentAllocator, DEFAULT_ALLOCATOR

logger = logging.getLogger(__name__)


def create_default_specialists() -> list[SpecialistAuditor]:
    """Instantiate the standard 8 specialist auditors."""
    return [
        ConsistencyAuditor(),
        CreativityAuditor(),
        ReaderHookAuditor(),
        EmotionCurveAuditor(),
        StyleAuditor(),
        FactualAuditor(),
        StructureAuditor(),
        MultimodalAuditor(),
    ]


def load_audit_weights(
    config_path: str = "config/audit_weights.yaml",
    genre: str = "",
    phase: str = "",
) -> dict[str, float]:
    """Load audit weights from YAML with genre/phase overrides."""
    import yaml

    default_weights = {
        "consistency": 0.20,
        "creativity": 0.15,
        "reader_hook": 0.15,
        "emotion_curve": 0.10,
        "style": 0.10,
        "factual": 0.10,
        "structure": 0.10,
        "multimodal": 0.10,
    }

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        weights = dict(data.get("default", default_weights))
        genre_overrides = data.get("by_genre", {})
        phase_overrides = data.get("by_phase", {})

        if genre and genre in genre_overrides:
            weights.update(genre_overrides[genre])
        if phase and phase in phase_overrides:
            weights.update(phase_overrides[phase])

        # Normalize to ensure sum is exactly 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights
    except Exception as e:
        logger.warning(f"Failed to load weights from {config_path} ({e}), using default weights")
        return default_weights


class AuditAggregatorNode:
    """Orchestrator node callable that runs 8 specialist auditors via AuditAggregator."""

    def __init__(
        self,
        aggregator: Optional[AuditAggregator] = None,
        weights_path: str = "config/audit_weights.yaml",
        event_bus: Any | None = None,
        repo: Any | None = None,
        llm: Any | None = None,
        experiment_allocator: Optional[ExperimentAllocator] = None,
        traffic_fraction: float = 0.01,
    ) -> None:
        self.weights_path = weights_path
        self.event_bus = event_bus
        self.repo = repo
        self.llm = llm
        self._aggregator = aggregator
        self._experiment_allocator = experiment_allocator or DEFAULT_ALLOCATOR
        # Allow runtime traffic fraction override
        if traffic_fraction != 0.01:
            self._experiment_allocator = ExperimentAllocator(traffic_fraction=traffic_fraction)
        # Load weight variants from YAML on init
        try:
            load_variants_from_yaml(weights_path)
        except Exception as e:
            logger.warning(f"Could not load weight variants from {weights_path}: {e}")

    def get_aggregator(self, genre: str = "", phase: str = "", book_id: int = 0) -> AuditAggregator:
        """Get or build AuditAggregator with appropriate weights (including A/B variant)."""
        if self._aggregator is not None:
            return self._aggregator

        # Use experiment allocator for A/B variant selection
        variant_name = self._experiment_allocator.allocate(book_id, genre)
        from src.config.weight_variants import get_variant
        weights = get_variant(variant_name)

        specialists = create_default_specialists()
        agg = AuditAggregator(
            specialists=specialists,
            weights=weights,
            event_bus=self.event_bus,
        )
        # Store variant name for metrics
        agg._weight_variant = variant_name
        return agg

    def build_specialist_input(self, ctx: AgentContext) -> dict[str, Any]:
        """Convert AgentContext into input dict required by specialist auditors."""
        draft_text = (
            ctx.artifacts.get("enriched_text")
            or ctx.artifacts.get("drafted_text")
            or ctx.artifacts.get("content")
            or ""
        )
        return {
            "book_id": ctx.book_id,
            "branch_id": ctx.branch_id,
            "ep_num": ctx.ep_num,
            "draft_text": draft_text,
            "writing_context": ctx.artifacts.get("writing_context", {}),
            "world_bible_snapshot": ctx.artifacts.get("world_bible_snapshot", {}),
            "world_bible": (
                ctx.artifacts.get("world_bible")
                or ctx.artifacts.get("world_bible_snapshot")
                or {}
            ),
            "genre": ctx.artifacts.get("genre", ""),
            "phase": ctx.artifacts.get("phase", "writing"),
            "plot_tree": ctx.artifacts.get("plot_tree") or ctx.artifacts.get("plot_summary", ""),
            "illustration_prompt": (
                ctx.artifacts.get("illustration_prompt")
                or ctx.artifacts.get("illustration_prompts")
                or ""
            ),
            "illustration_prompts": (
                ctx.artifacts.get("illustration_prompts")
                or ctx.artifacts.get("illustration_prompt")
                or ""
            ),
            "style_dna": ctx.artifacts.get("style_dna", {}),
        }

    def to_agent_result(
        self,
        score_result: BookScoreResult,
        ctx: AgentContext,
        min_pass_score: float = 70.0,
        max_retries: int = 2,
    ) -> AgentResult:
        """Convert BookScoreResult into AgentResult for downstream pipeline.

        If overall score < min_pass_score and within retry limit, trigger
        targeted regeneration by routing back to WRITING with guidance
        focused on the lowest scoring dimension.
        """
        audit_payload = score_result.to_dict()
        lowest_dim = score_result.lowest_dimension()
        retry_count = int(ctx.artifacts.get("audit_retry_count", 0))

        # Retrieve suggestions for lowest dimension
        suggestions = []
        if lowest_dim and lowest_dim in score_result.raw:
            suggestions = score_result.raw[lowest_dim].suggestions

        regeneration_directive = ""
        if lowest_dim:
            sugg_text = "、".join(suggestions) if suggestions else "全体的な描写と整合性の見直し"
            regeneration_directive = f"【再生成指示 - 重点改善項目: {lowest_dim}】\nスコア向上のため以下を反映して書き直してください: {sugg_text}"

        artifacts = {
            "audit_report": audit_payload,
            "audit_score": score_result.overall,
            "specialist_scores": score_result.by_specialist,
            "lowest_dimension": lowest_dim,
            "missing_specialists": score_result.missing,
            "audit_retry_count": retry_count,
            "regeneration_directive": regeneration_directive,
        }

        # Check if regeneration is required
        if score_result.overall < min_pass_score and retry_count < max_retries:
            artifacts["audit_retry_count"] = retry_count + 1
            logger.info(
                "BookScore %.2f < %.2f (retry %d/%d). Triggering regeneration for %s.",
                score_result.overall,
                min_pass_score,
                retry_count + 1,
                max_retries,
                lowest_dim,
            )
            return AgentResult(
                next_agent=AgentName.WRITING,
                artifacts=artifacts,
                should_retry=True,
                error=None,
            )

        # Passed audit or reached max retries -> proceed to ILLUSTRATION
        return AgentResult(
            next_agent=AgentName.ILLUSTRATION,
            artifacts=artifacts,
            should_retry=False,
            error=None,
        )

    def save_specialist_results(
        self,
        book_id: int,
        chapter_number: int,
        raw_results: dict[str, Any],
        session: Any = None,
    ) -> None:
        """Persist individual specialist audit results into audit_specialist_results table."""
        if not session and self.repo and hasattr(self.repo, "session"):
            session = self.repo.session

        if not session:
            return

        import json
        from datetime import datetime, timezone
        from sqlalchemy import text

        now = datetime.now(timezone.utc)
        for sp_name, res in raw_results.items():
            score = getattr(res, "score", 0.0)
            feedback = json.dumps(getattr(res, "feedback", {}), ensure_ascii=False)
            suggestions = json.dumps(getattr(res, "suggestions", []), ensure_ascii=False)

            try:
                # PostgreSQL upsert or fallback insert
                query = text("""
                    INSERT INTO audit_specialist_results 
                        (book_id, chapter_number, specialist_name, score, feedback_json, suggestions_json, evaluated_at, evaluator_version)
                    VALUES 
                        (:book_id, :chapter_number, :specialist_name, :score, :feedback_json, :suggestions_json, :evaluated_at, :evaluator_version)
                    ON CONFLICT (book_id, chapter_number, specialist_name) 
                    DO UPDATE SET
                        score = EXCLUDED.score,
                        feedback_json = EXCLUDED.feedback_json,
                        suggestions_json = EXCLUDED.suggestions_json,
                        evaluated_at = EXCLUDED.evaluated_at,
                        evaluator_version = EXCLUDED.evaluator_version
                """)
                session.execute(
                    query,
                    {
                        "book_id": book_id,
                        "chapter_number": chapter_number,
                        "specialist_name": sp_name,
                        "score": float(score),
                        "feedback_json": feedback,
                        "suggestions_json": suggestions,
                        "evaluated_at": now,
                        "evaluator_version": "v2-pipeline",
                    },
                )
            except Exception as ex:
                logger.debug(f"Failed to persist specialist audit result for {sp_name}: {ex}")

        try:
            session.commit()
        except Exception as ex:
            logger.debug(f"Failed to commit specialist audit results: {ex}")

    async def __call__(self, ctx: AgentContext) -> AgentResult:
        """Main execution entrypoint conforming to AgentNode signature."""
        try:
            genre = ctx.artifacts.get("genre", "")
            phase = ctx.artifacts.get("phase", "writing")
            book_id = ctx.book_id
            aggregator = self.get_aggregator(genre=genre, phase=phase, book_id=book_id)

            specialist_input = self.build_specialist_input(ctx)
            await aggregator.run_all(specialist_input)
            score_result = aggregator.aggregate()

            # Include weight variant in score result for metrics
            variant_name = getattr(aggregator, "_weight_variant", "default_v1")
            if not hasattr(score_result, "weight_variant"):
                # Add variant info to raw results for metrics collection
                for res in score_result.raw.values():
                    res.feedback["weight_variant"] = variant_name

            # Pass weight variant to context for event publishing
            specialist_input["weight_variant"] = variant_name

            # Persist specialist results to DB if session is available
            session = ctx.artifacts.get("session") or ctx.artifacts.get("db_session")
            self.save_specialist_results(
                book_id=book_id,
                chapter_number=ctx.ep_num,
                raw_results=score_result.raw,
                session=session,
            )

            # Publish aggregated metrics for A/B test analysis
            try:
                await aggregator.publish_aggregated_metrics(score_result, specialist_input)
            except Exception as e:
                logger.debug(f"Failed to publish aggregated metrics: {e}")

            return self.to_agent_result(score_result, ctx)
        except Exception as e:
            logger.exception(f"AuditAggregatorNode execution failed: {e}")
            return AgentResult(
                next_agent=AgentName.ILLUSTRATION,
                artifacts={"audit_error": str(e)},
                should_retry=False,
                error=f"Audit aggregation failed: {e}",
            )

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Alias for Orchestrator node compatibility."""
        return await self(ctx)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """Alias for SkillAgent compatibility."""
        return await self(ctx)

