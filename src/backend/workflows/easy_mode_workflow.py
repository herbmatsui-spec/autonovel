"""
EasyModeWorkflow - 統合パイプラインへ委譲
既存インターフェース完全互換維持
"""

from __future__ import annotations

import logging
import os
from typing import Any

from src.backend.workflows.base_workflow import BaseWorkflow
from src.services.auto_workflow_pipeline import (
    WorkflowContext,
    create_easy_mode_pipeline,
)
from src.services.pipeline_param_mapper import (
    map_easymode_kwargs_to_context,
    map_context_to_easymode_result,
)
from src.services.progress_reporter import UnifiedProgressReporter
from src.shared.utils import StatusReporter

USE_UNIFIED = os.getenv("USE_UNIFIED_PIPELINE", "1") == "1"

logger = logging.getLogger(__name__)


class EasyModeWorkflow(BaseWorkflow):
    """
    かんたんモードの全自動小説生成パイプラインを実行するワークフロー。
    統合パイプライン (AutoWorkflowPipeline) に委譲。
    """

    async def execute(
        self,
        reporter: StatusReporter,
        genre: str = "ファンタジー",
        keywords: list[str] | None = None,
        protagonist_type: str = "チート主人公",
        target_episodes: int = 10,
        words_per_episode: int = 2000,
        enable_audit: bool = True,
        max_rewrites: int = 2,
        **kwargs: Any,
    ) -> dict[str, Any]:
        logger.info(f"EasyModeWorkflow started: genre={genre}, target_episodes={target_episodes}")

        if not USE_UNIFIED:
            logger.warning(
                "USE_UNIFIED_PIPELINE=0 is set, but the old implementation is not available. Falling back to unified pipeline."
            )

        # 1. 統合パイプライン用 Context 構築
        ctx = map_easymode_kwargs_to_context(
            genre=genre,
            keywords=keywords,
            protagonist_type=protagonist_type,
            target_episodes=target_episodes,
            words_per_episode=words_per_episode,
            enable_audit=enable_audit,
            max_rewrites=max_rewrites,
            **kwargs,
        )

        # 2. パイプライン構築・実行
        pipeline = create_easy_mode_pipeline(
            genre=genre,
            target_episodes=target_episodes,
            enable_spice_guard=enable_audit,
            max_rewrite_iterations=max_rewrites,
            target_audit_score=95.0,
            enable_marketing=True,
        )

        adapter = UnifiedProgressReporter(reporter=reporter)
        result = await pipeline.execute(ctx, self.engine, adapter)

        # 3. 既存インターフェース互換の dict に変換
        return map_context_to_easymode_result(ctx, result)


__all__ = ["EasyModeWorkflow"]
