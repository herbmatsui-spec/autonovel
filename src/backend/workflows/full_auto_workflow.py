"""
FullAutoWorkflow - 統合パイプラインへ委譲
既存インターフェース完全互換維持
"""

from __future__ import annotations

import logging
import os
from typing import Any

from src.backend.workflows.base_workflow import BaseWorkflow
from src.services.auto_workflow_pipeline import create_full_auto_pipeline
from src.services.pipeline_param_mapper import (
    map_context_to_fullauto_result,
    map_fullauto_kwargs_to_context,
)
from src.services.progress_reporter import ProgressReporterAdapter
from src.shared.utils import StatusReporter

USE_UNIFIED = os.getenv("USE_UNIFIED_PIPELINE", "1") == "1"

logger = logging.getLogger(__name__)


class FullAutoWorkflow(BaseWorkflow):
    """かんたんモード: 企画・執筆・パッケージングの一連のフローを実行 (統合パイプライン版)"""

    async def execute(self, reporter: StatusReporter, **kwargs) -> dict[str, Any]:
        if not USE_UNIFIED:
            raise NotImplementedError(
                "USE_UNIFIED_PIPELINE=0 is no longer supported. "
                "The legacy implementation was removed in the pipeline unification. "
                "Use USE_UNIFIED_PIPELINE=1 (default)."
            )

        # 1. 統合パイプライン用 Context 構築
        ctx = map_fullauto_kwargs_to_context(kwargs)

        # 2. パイプライン構築・実行
        pipeline = create_full_auto_pipeline(
            enable_spice_guard=ctx.enable_spice_guard,
            enable_illustration=ctx.enable_illustration,
            enable_catharsis_analysis=ctx.enable_catharsis_analysis,
            enable_marketing=ctx.enable_marketing,
            max_retries=ctx.max_retries,
        )

        adapter = ProgressReporterAdapter(reporter, is_easy_mode=False)
        result = await pipeline.execute(ctx, self.engine, adapter)

        # 3. 既存インターフェース互換の dict に変換
        return map_context_to_fullauto_result(ctx, result)
