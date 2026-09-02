"""
FullAutoWorkflow - 統合パイプラインへ委譲
既存インターフェース完全互換維持
"""

from __future__ import annotations

from typing import Any

from src.backend.workflows.base_workflow import BaseWorkflow
from src.services.auto_workflow_pipeline import (
    WorkflowContext,
    create_full_auto_pipeline,
)
from src.shared.utils import StatusReporter


class FullAutoWorkflow(BaseWorkflow):
    """かんたんモード: 企画・執筆・パッケージングの一連のフローを実行 (統合パイプライン版)"""

    async def execute(self, reporter: StatusReporter, **kwargs) -> dict[str, Any]:
        # 1. 統合パイプライン用 Context 構築
        ctx = WorkflowContext(
            genre=kwargs["genre"],
            keywords=kwargs["keywords"],
            archetype_key=kwargs["archetype_key"],
            target_eps=kwargs["target_eps"],
            initial_limit=kwargs["initial_limit"],
            word_count=kwargs["word_count"],
            concept=kwargs.get("concept", ""),
            tone_vibe=kwargs.get("tone_vibe", 0.6),
            user_prompt=kwargs.get("user_prompt", ""),
            enable_illustration=bool(kwargs.get("illustration_settings", {}).get("enableIllustration", False)),
            illustration_settings=kwargs.get("illustration_settings", {}),
            enable_spice_guard=kwargs.get("enable_spice_guard", False),
            enable_catharsis_analysis=True,
            enable_marketing=True,
            max_retries=1,
            is_easy_mode=False,
        )

        # 2. パイプライン構築・実行
        pipeline = create_full_auto_pipeline(
            enable_spice_guard=ctx.enable_spice_guard,
            enable_illustration=ctx.enable_illustration,
            enable_catharsis_analysis=ctx.enable_catharsis_analysis,
            enable_marketing=ctx.enable_marketing,
            max_retries=ctx.max_retries,
        )

        result = await pipeline.execute(ctx, self.engine, reporter)

        # 3. 既存インターフェース互換の dict に変換
        return {
            "book_id": result.book_id,
            "title": result.title,
            "chars_count": result.chars_count,
            "failed_episodes": result.failed_episodes,
            "zip_data": result.zip_data,
            "zip_filename": result.zip_filename,
            "illustrations": result.illustrations,
            "status": result.status,
            "easy_parameters": result.easy_parameters,
            "average_audit_score": result.average_audit_score,
            "episodes_detail": result.episodes_detail,
        }