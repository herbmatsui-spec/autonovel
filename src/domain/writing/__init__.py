"""WritingService Facade - 統合執筆サービスの公開API."""

from __future__ import annotations

from typing import Any

from src.domain.writing.coordinator import WritingCoordinator
from src.domain.writing.models import (
    WritingGenerationContext,
    clean_writing_response,
    DIMENSION_ACTIONS,
    RegenerationAction,
)
from src.domain.writing.quality_loop import QualityLoop
from src.domain.writing.state_guard import StateGuard, ValidationResult


class WritingService:
    """
    統合執筆サービスファサード。
    
    WritingCoordinator, QualityLoop, StateGuard を束ね、
    後方互換性を持つ単一の公開APIを提供する。
    """

    def __init__(
        self,
        # Coordinator dependencies
        writer: Any = None,
        repo: Any = None,
        pm: Any = None,
        style_rag: Any = None,
        ctx_mgr: Any = None,
        reporter_factory: Any = None,
        book_score_calculator: Any = None,
        score_threshold: float = 70.0,
        # QualityLoop dependencies
        writing_agent: Any = None,
        context_builder_agent: Any = None,
        illustration_agent: Any = None,
        compressor: Any = None,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        anti_ai_controller: Any = None,
        enable_anti_ai_loop: bool = True,
        anti_ai_threshold: float = 85.0,
    ) -> None:
        # Coordinator に渡す引数を準備
        coordinator_kwargs = {
            "writer": writer or writing_agent,
            "repo": repo,
            "pm": pm,
            "style_rag": style_rag,
            "ctx_mgr": ctx_mgr,
            "reporter_factory": reporter_factory,
            "book_score_calculator": book_score_calculator,
            "score_threshold": score_threshold,
        }

        # QualityLoop に渡す引数を準備
        quality_loop_kwargs = {
            "writing_agent": writing_agent or writer,
            "book_score_calculator": book_score_calculator,
            "context_builder_agent": context_builder_agent,
            "illustration_agent": illustration_agent,
            "compressor": compressor,
            "max_retries": max_retries,
            "score_threshold": score_threshold,
            "backoff_base": backoff_base,
            "anti_ai_controller": anti_ai_controller,
            "enable_anti_ai_loop": enable_anti_ai_loop,
            "anti_ai_threshold": anti_ai_threshold,
        }

        # StateGuard に渡す引数
        state_guard_kwargs = {
            "repo": repo,
        }

        self._coordinator = WritingCoordinator(**coordinator_kwargs)
        self._quality_loop = QualityLoop(**quality_loop_kwargs)
        self._state_guard = StateGuard(**state_guard_kwargs)
        
        # Backward compatibility: expose internal agents
        self.context_builder_agent = context_builder_agent
        self.illustration_agent = illustration_agent
        self.writing_agent = writing_agent or writer
        self.compressor = compressor

    # === WritingCoordinator methods (pipeline execution) ===

    async def generate_episodes_pipeline(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> tuple[int, list[Any]]:
        return await self._coordinator.generate_episodes_pipeline(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
        )

    async def generate_episodes(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
        auto_regenerate: bool = True,
        max_retries: int = 3,
    ) -> int:
        return await self._coordinator.generate_episodes(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
            auto_regenerate=auto_regenerate,
            max_retries=max_retries,
        )

    def audit_generated_text(self, text: str) -> dict[str, Any]:
        return self._coordinator.audit_generated_text(text)

    async def calculate_book_score(
        self,
        book_id: int,
        chapter_number: int,
        genre: str = "",
        phase: str = "writing",
    ) -> dict[str, float] | None:
        return await self._coordinator.calculate_book_score(
            book_id=book_id,
            chapter_number=chapter_number,
            genre=genre,
            phase=phase,
        )

    async def analyze_and_import_chapter(
        self,
        book_id: int,
        ep_num: int,
        import_text: str,
        do_refine: bool = True,
    ) -> Any:
        return await self._coordinator.analyze_and_import_chapter(
            book_id=book_id,
            ep_num=ep_num,
            import_text=import_text,
            do_refine=do_refine,
        )

    # === QualityLoop methods (quality assurance) ===

    async def generate_with_quality_assurance(
        self,
        ctx: Any,
        reporter: Any = None,
    ) -> Any:
        return await self._quality_loop.evaluate_and_regenerate(ctx, reporter)

    async def _build_context_with_compression(self, ctx: Any) -> dict[str, Any]:
        """Delegate to QualityLoop's _build_context_with_compression."""
        return await self._quality_loop._build_context_with_compression(ctx)

    # === StateGuard methods (validation) ===

    def validate_project_context(self, project_ctx: Any) -> ValidationResult:
        return self._state_guard.validate_project_context(project_ctx)

    async def ensure_chapter_sequence(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
    ) -> bool:
        return await self._state_guard.ensure_chapter_sequence(book_id, start_ep, end_ep)

    def validate_writing_context(self, ctx: dict[str, Any]) -> ValidationResult:
        return self._state_guard.validate_writing_context(ctx)

    # === Shared models (re-exported for backward compatibility) ===

    WritingGenerationContext = WritingGenerationContext
    clean_writing_response = staticmethod(clean_writing_response)
    RegenerationAction = RegenerationAction
    DIMENSION_ACTIONS = DIMENSION_ACTIONS


# Backward compatibility aliases
WritingServices = WritingService


__all__ = [
    "WritingService",
    "WritingServices",
    "WritingCoordinator",
    "QualityLoop",
    "StateGuard",
    "ValidationResult",
    "WritingGenerationContext",
    "clean_writing_response",
    "RegenerationAction",
    "DIMENSION_ACTIONS",
]