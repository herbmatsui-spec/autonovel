"""
EasyModeWorkflow - 統合パイプラインへ委譲
既存インターフェース完全互換維持
"""

from __future__ import annotations

import logging
from typing import Any

from src.backend.workflows.base_workflow import BaseWorkflow
from src.services.auto_workflow_pipeline import (
    WorkflowContext,
    create_easy_mode_pipeline,
)
from src.shared.utils import StatusReporter

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
        logger.info(
            f"EasyModeWorkflow started: genre={genre}, target_episodes={target_episodes}"
        )

        # 1. 進捗コールバックアダプタ (既存互換)
        def progress_callback(stage: str, current: int, total: int):
            stage_messages = {
                "bible": ("Bible生成中", f"ジャンル設定反映中... ({current}/{total})"),
                "plot": ("プロット生成中", f"全{total}話の構成作成中... ({current}/{total})"),
                "writing": ("本文執筆中", f"第{current}話を執筆中... ({current}/{total})"),
                "episode_complete": ("話完了", f"第{current}話が完了 ({current}/{total})"),
                "finalizing": ("完結処理中", f"メタデータ生成中... ({current}/{total})"),
            }
            msg, sub_msg = stage_messages.get(stage, (stage, ""))
            reporter.update_progress(current, total, msg, sub_msg)

        # 2. 統合パイプライン用 Context 構築
        ctx = WorkflowContext(
            genre=genre,
            keywords=", ".join(keywords) if keywords else "",
            archetype_key=protagonist_type,
            target_eps=target_episodes,
            initial_limit=3,
            word_count=words_per_episode,
            concept=kwargs.get("concept", ""),
            tone_vibe=kwargs.get("tone_vibe", 0.6),
            user_prompt=kwargs.get("user_prompt", ""),
            enable_spice_guard=enable_audit,
            max_rewrite_iterations=max_rewrites,
            target_audit_score=95.0,
            enable_illustration=False,
            enable_catharsis_analysis=False,
            enable_marketing=True,
            max_retries=0,
            is_easy_mode=True,
            preset_name=kwargs.get("preset_name", ""),
        )

        # 3. パイプライン構築・実行
        pipeline = create_easy_mode_pipeline(
            genre=genre,
            target_episodes=target_episodes,
            enable_spice_guard=enable_audit,
            max_rewrite_iterations=max_rewrites,
            target_audit_score=95.0,
            enable_marketing=True,
        )

        result = await pipeline.execute(ctx, self.engine, reporter)

        # 4. 既存インターフェース互換の dict に変換
        episodes_list = []
        for ep in result.episodes_detail:
            episodes_list.append({
                "episode_num": ep.get("episode_num", 0),
                "title": ep.get("title", f"第{ep.get('episode_num', 0)}話"),
                "word_count": ep.get("word_count", 0),
                "audit_score": ep.get("audit_score", 0.0),
                "audit_passed": ep.get("audit_passed", False),
                "rewrite_count": ep.get("rewrite_count", 0),
                "needs_human_review": ep.get("needs_human_review", False),
            })

        return {
            "title": result.title,
            "concept": result.easy_parameters.get("concept", ""),
            "total_episodes": result.easy_parameters.get("target_eps", target_episodes),
            "total_words": result.chars_count,
            "average_audit_score": result.average_audit_score,
            "genre": genre,
            "episodes": episodes_list,
            "status": result.status,
        }


__all__ = ["EasyModeWorkflow"]