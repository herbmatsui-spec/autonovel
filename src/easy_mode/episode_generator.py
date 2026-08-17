"""
エピソード生成モジュール
"""

import logging
from typing import Any, Dict, List

from src.easy_mode.context_helper import build_prev_context
from src.easy_mode.models import EpisodeResult

logger = logging.getLogger(__name__)


class EpisodeGenerator:
    """エピソード生成（執筆→監査→リライト）"""

    def __init__(
        self,
        episode_writer,
        episode_auditor,
        episode_rewriter,
        config,
    ):
        self.episode_writer = episode_writer
        self.episode_auditor = episode_auditor
        self.episode_rewriter = episode_rewriter
        self.config = config

    async def generate(
        self,
        ep_num: int,
        bible: Dict[str, Any],
        plot_outline: List[Dict[str, Any]],
        previous_episodes: List[EpisodeResult],
    ) -> EpisodeResult:
        """1話生成（執筆→監査→リライト）"""
        plot = plot_outline[ep_num - 1]

        # 前話までの要約作成
        prev_context = build_prev_context(previous_episodes, self.config.context_window, self.config.context_window_min_reserve)

        # 執筆
        content = await self.episode_writer.write(ep_num, bible, plot, prev_context)

        # 監査
        audit_result = await self.episode_auditor.audit(
            content, bible, plot, ep_num, self.config.genre
        )

        # リライト（SpiceGuard付き）
        final_content = content
        rewrite_count = 0
        spice_elements: List[Any] = []

        if self.config.enable_spice_guard:
            spice_elements = self.episode_rewriter.extract_spice(content)

        for rewrite_iter in range(self.config.max_rewrite_iterations):
            if audit_result.score >= self.config.target_audit_score:
                break

            if rewrite_iter >= self.config.max_rewrite_iterations - 1:
                # 最後の試行でもダメなら人間レビューフラグ
                audit_result.needs_human_review = True
                break

            # 改善指示でリライト
            improvements = audit_result.improvements
            final_content = await self.episode_rewriter.rewrite(
                final_content, improvements, spice_elements
            )

            # 再監査
            audit_result = await self.episode_auditor.audit(
                final_content, bible, plot, ep_num, self.config.genre
            )
            rewrite_count += 1

        return EpisodeResult(
            episode_num=ep_num,
            title=plot["title"],
            content=final_content,
            word_count=len(final_content),
            audit_score=audit_result.score,
            audit_passed=audit_result.passed,
            rewrite_count=rewrite_count,
            spice_elements=spice_elements,
            metadata={"plot": plot, "audit_details": audit_result.details},
            needs_human_review=audit_result.needs_human_review,
        )
