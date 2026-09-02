"""かんたんモード（小説完全自律生成）ワークフロー。"""
from __future__ import annotations

import logging
from typing import Any

from src.backend.workflows.base_workflow import BaseWorkflow
from src.easy_mode.pipeline import EasyModePipeline, PipelineConfig
from src.shared.utils import StatusReporter

logger = logging.getLogger(__name__)


class EasyModeWorkflow(BaseWorkflow):
    """
    かんたんモードの全自動小説生成パイプラインを実行するワークフロー。
    Bible生成 -> プロット生成 -> 本文執筆 -> 推敲監査 -> 完結処理を一貫してオーケストレーションする。
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

        config = PipelineConfig(
            genre=genre,
            keywords=keywords or [],
            protagonist_type=protagonist_type,
            target_episodes=target_episodes,
            words_per_episode=words_per_episode,
            enable_audit=enable_audit,
            max_rewrites=max_rewrites,
        )

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

        config.progress_callback = progress_callback

        pipeline = EasyModePipeline(self.engine, config)
        result = await pipeline.run()

        logger.info(f"EasyModeWorkflow completed: title={result.title}")
        return {
            "title": result.title,
            "concept": result.concept,
            "total_episodes": result.total_episodes,
            "total_words": sum(ep.word_count for ep in result.episodes),
            "average_audit_score": (
                round(sum(ep.audit_score for ep in result.episodes) / len(result.episodes), 1)
                if result.episodes
                else 0
            ),
            "genre": result.genre,
            "episodes": [
                {
                    "episode_num": ep.episode_num,
                    "title": ep.title,
                    "word_count": ep.word_count,
                    "audit_score": ep.audit_score,
                    "audit_passed": ep.audit_passed,
                    "rewrite_count": ep.rewrite_count,
                    "needs_human_review": ep.needs_human_review,
                }
                for ep in result.episodes
            ],
        }


__all__ = ["EasyModeWorkflow"]
