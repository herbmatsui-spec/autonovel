"""QualityLoop - BookScore評価と再生成ループ."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.illustration_agent import IllustrationAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.writing import WritingAgent
from src.services.book_score_service import BookScoreCalculator

try:
    from src.services.anti_ai.loop_controller import AntiAILoopController
except ImportError:
    AntiAILoopController: type[Any] | None = None

from src.domain.writing.models import DIMENSION_ACTIONS, RegenerationAction

logger = logging.getLogger(__name__)


class QualityLoop:
    """BookScore連携・自動再生成ループを持つ品質保証コンポーネント."""

    def __init__(
        self,
        writing_agent: WritingAgent,
        book_score_calculator: BookScoreCalculator,
        context_builder_agent: ContextBuilderAgent,
        illustration_agent: IllustrationAgent,
        compressor: Any = None,
        max_retries: int = 3,
        score_threshold: float = 70.0,
        backoff_base: float = 2.0,
        anti_ai_controller: Optional[Any] = None,
        enable_anti_ai_loop: bool = True,
        anti_ai_threshold: float = 85.0,
    ):
        self.writing_agent = writing_agent
        self.book_score_calculator = book_score_calculator
        self.context_builder_agent = context_builder_agent
        self.illustration_agent = illustration_agent
        self.compressor = compressor
        self.max_retries = max_retries
        self.score_threshold = score_threshold
        self.backoff_base = backoff_base
        self._anti_ai_controller = anti_ai_controller
        self._enable_anti_ai_loop = enable_anti_ai_loop and AntiAILoopController is not None
        self._anti_ai_threshold = anti_ai_threshold

    async def _build_context_with_compression(self, ctx: AgentContext) -> dict:
        """compressor 付きでコンテキスト構築"""
        # ContextBuilderAgent が compressor を使うよう artifacts に設定
        ctx.artifacts["compressor"] = self.compressor
        result = await self.context_builder_agent.execute(ctx)
        return result.artifacts.get("writing_context", {})

    async def evaluate_and_regenerate(
        self,
        ctx: AgentContext,
        reporter: Any = None,
    ) -> AgentResult:
        """
        品質保証付き執筆実行
        BookScore が閾値未満の場合、自動的に再生成を試行
        """
        retry_count = 0
        regeneration_history = []

        while retry_count <= self.max_retries:
            # 1. 通常執筆実行
            if reporter:
                reporter.report(f"執筆実行 (試行 {retry_count + 1}/{self.max_retries + 1})", "info")

            # compressor を artifacts に設定して context_builder_agent などで利用可能にする
            ctx.artifacts["compressor"] = self.compressor
            result = await self.writing_agent.execute(ctx)

            if result.error:
                logger.warning(f"WritingAgent エラー: {result.error}")
                return result

            # 2. Anti-AI 修正ループ (オプション)
            anti_ai_result = None
            if self._enable_anti_ai_loop and hasattr(result, "draft_text") and result.draft_text:
                if reporter:
                    reporter.report("Anti-AI 修正実行中...", "info")

                controller = self._anti_ai_controller or AntiAILoopController(
                    max_loops=3,
                    score_threshold=self._anti_ai_threshold,
                )
                anti_ai_result = await controller.run(result.draft_text)
                result.draft_text = anti_ai_result.text

                if reporter:
                    reporter.report(
                        f"Anti-AI 修正完了: スコア={anti_ai_result.final_score:.1f}, "
                        f"イテレーション={anti_ai_result.iterations}",
                        "info",
                    )

            # 3. BookScore 計算
            if reporter:
                reporter.report("BookScore 計算中...", "info")

            book_score = await self.book_score_calculator.calculate(
                book_id=ctx.book_id,
                chapter_number=ctx.ep_num,
                ctx=ctx,
            )

            overall_score = book_score.overall_score

            if reporter:
                reporter.report(f"BookScore: {overall_score:.1f} 点 (閾値: {self.score_threshold})", "info")

            # 4. 閾値チェック
            if overall_score >= self.score_threshold:
                if reporter:
                    reporter.report(f"品質基準クリア ({overall_score:.1f} >= {self.score_threshold})", "success")
                return result

            # 5. 再生成判定
            retry_count += 1
            if retry_count > self.max_retries:
                logger.warning(f"最大リトライ回数到達 ({self.max_retries})、品質基準未達のまま完了")
                return result

            # 6. 低スコア次元特定
            low_dimensions = self._identify_low_dimensions(book_score)
            if not low_dimensions:
                logger.warning("低スコア次元が特定できません")
                return result

            # 7. 再生成アクション決定
            action = self._determine_regeneration_action(low_dimensions)
            regeneration_history.append({
                "attempt": retry_count,
                "score": overall_score,
                "low_dimensions": low_dimensions,
                "action": action.focus_dimensions,
            })

            if reporter:
                reporter.report(f"再生成実行: 対象次元={action.focus_dimensions}", "warning")

            # 8. コンテキスト更新 (regeneration_focus 設定)
            ctx.artifacts["regeneration_focus"] = action.focus_dimensions
            ctx.artifacts["regeneration_action"] = action
            ctx.artifacts["regeneration_history"] = regeneration_history
            if anti_ai_result:
                ctx.artifacts["anti_ai_loop_result"] = anti_ai_result.to_dict()

            # 9. バックオフ待機
            wait_time = self.backoff_base ** retry_count
            if reporter:
                reporter.report(f"{wait_time:.1f}秒待機後、再生成実行", "info")
            await asyncio.sleep(wait_time)

        return result

    def _identify_low_dimensions(self, book_score: Any) -> list[str]:
        """閾値未満の次元を特定"""
        dims = {
            "structure": book_score.structure_score,
            "coherency": book_score.coherency_score,
            "factual_grounding": book_score.factual_grounding_score,
            "visual_textual_synergy": book_score.visual_textual_synergy_score,
            "reader_experience": book_score.reader_experience_score,
        }
        return [dim for dim, score in dims.items() if score < self.score_threshold]

    def _determine_regeneration_action(self, low_dimensions: list[str]) -> RegenerationAction:
        """複数の低次元から最優先アクションを決定"""
        # 優先度順でソート
        sorted_dims = sorted(low_dimensions, key=lambda d: DIMENSION_ACTIONS[d].priority)
        return DIMENSION_ACTIONS[sorted_dims[0]]