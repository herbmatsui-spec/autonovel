"""
かんたんモード パイプライン（オーケストレーション専用）
ジャンル選択のみで企画〜完結まで全自動生成
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from config.settings import get_settings
from src.core.async_utils import limit_concurrency
from src.core.exceptions import (
    BibleGenerationError,
    EpisodeAuditError,
    EpisodeRewriteError,
    EpisodeWritingError,
    PlotGenerationError,
    SeriesFinalizationError,
    PipelineError,
)
from src.easy_mode.bible_generator import BibleGenerator
from src.easy_mode.episode_auditor import EpisodeAuditor
from src.easy_mode.episode_rewriter import EpisodeRewriter
from src.easy_mode.episode_writer import EpisodeWriter
from src.easy_mode.models import EpisodeResult, PipelineConfig, RetryConfig, SeriesResult
from src.easy_mode.plot_generator import PlotGenerator
from src.easy_mode.progress_reporter import ProgressReporter
from src.easy_mode.series_finalizer import SeriesFinalizer
from src.easy_mode.context_helper import build_prev_context
from src.easy_mode.episode_generator import EpisodeGenerator
logger = logging.getLogger(__name__)


class EasyModePipeline:
    """かんたんモード 全自動生成パイプライン（オーケストレーション専用）"""

    def __init__(
        self,
        engine,
        config: PipelineConfig,
        # DI: 各モジュールを注入可能（テスタビリティ向上）
        bible_generator: Optional[BibleGenerator] = None,
        plot_generator: Optional[PlotGenerator] = None,
        episode_writer: Optional[EpisodeWriter] = None,
        episode_auditor: Optional[EpisodeAuditor] = None,
        episode_rewriter: Optional[EpisodeRewriter] = None,
        series_finalizer: Optional[SeriesFinalizer] = None,
        progress_reporter: Optional[ProgressReporter] = None,
        episode_generator: Optional[EpisodeGenerator] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.engine = engine
        self.config = config
        self.preset = load_preset(config.genre)
        self._cancelled = False

        # リトライ設定
        self.retry_config = retry_config or RetryConfig()

        # サブモジュール初期化（DI未指定なら自動生成）
        self.bible_generator = bible_generator or BibleGenerator(
            self.preset, engine.llm, self.retry_config
        )
        self.plot_generator = plot_generator or PlotGenerator(
            self.preset, config.target_episodes
        )
        self.episode_writer = episode_writer or EpisodeWriter(
            engine.llm, self.preset, self.retry_config
        )
        self.episode_auditor = episode_auditor or EpisodeAuditor(
            engine.auditor, config.target_audit_score
        )
        self.episode_rewriter = episode_rewriter or EpisodeRewriter(
            engine.llm, config.genre, self.retry_config
        )
        self.series_finalizer = series_finalizer or SeriesFinalizer(self.preset)
        self.progress_reporter = progress_reporter or ProgressReporter(config.progress_callback)
        self.episode_generator = episode_generator or EpisodeGenerator(
            self.episode_writer, self.episode_auditor, self.episode_rewriter, self.config
        )

        # キャンセル伝播
        self._submodules = [
            self.bible_generator,
            self.plot_generator,
            self.episode_writer,
            self.episode_auditor,
            self.episode_rewriter,
            self.series_finalizer,
            self.episode_generator,
        ]
    async def run(self) -> SeriesResult:
        """パイプライン全体を実行"""
        logger.info(f"Starting easy mode pipeline for genre: {self.config.genre}")

        # キャンセル済みなら即座に空結果を返す
        if self._cancelled:
            logger.info("Pipeline cancelled before start")
            self._cancelled = False
            return SeriesResult(
                genre=self.config.genre,
                title="",
                concept="",
                total_episodes=0,
                episodes=[],
                bible={},
                plot_outline=[],
                metadata={},
                status="cancelled",
            )

        try:
            # Step 1: Bible生成
            await self.progress_reporter.report("bible", 0, self.config.target_episodes)
            bible = await limit_concurrency(self.bible_generator.generate(self.config.target_episodes))

            # Step 2: プロット生成（同期メソッド）
            await self.progress_reporter.report("plot", 0, self.config.target_episodes)
            plot_outline = self.plot_generator.generate(bible)

            # Step 3: 各話生成ループ
            episodes: list[EpisodeResult] = []
            for ep_num in range(1, self.config.target_episodes + 1):
                if self._cancelled:
                    logger.info(f"Pipeline cancelled at episode {ep_num}")
                    break

                await self.progress_reporter.report("writing", ep_num - 1, self.config.target_episodes)
                episode_result = await limit_concurrency(
                    self.episode_generator.generate(ep_num, bible, plot_outline, episodes)
                )
                episodes.append(episode_result)

            await self.progress_reporter.report("finalizing", len(episodes), self.config.target_episodes)
            finalize_data = await self.series_finalizer.finalize(bible, plot_outline, episodes)

            # 完了処理
            self._cancelled = False
            return SeriesResult(
                genre=self.config.genre,
                title=finalize_data["title"],
                concept=finalize_data["concept"],
                total_episodes=self.config.target_episodes,
                episodes=episodes,
                bible=bible,
                plot_outline=plot_outline,
                metadata=finalize_data,
            )

        except (BibleGenerationError, PlotGenerationError, EpisodeWritingError, EpisodeAuditError, EpisodeRewriteError, SeriesFinalizationError) as e:
            logger.error(f"Pipeline failed at stage: {e}", exc_info=True)
            self._cancelled = False
            raise
        except (KeyError, ValueError, TypeError, RuntimeError, AttributeError) as e:
            logger.error(f"Unexpected pipeline error: {e}", exc_info=True)
            self._cancelled = False
            raise PipelineError(f"Unexpected error: {e}", original=e) from e

    def cancel(self):
        """キャンセル"""
        self._cancelled = True
        # サブモジュールにも伝播
        for module in self._submodules:
            if hasattr(module, "cancel"):
                module.cancel()

    # === 後方互換メソッド（既存テスト・コードのため） ===
    async def _generate_bible(self) -> dict[str, Any]:
        """Bible生成（後方互換）"""
        return await self.bible_generator.generate(self.config.target_episodes)

    async def _generate_plot_outline(self, bible: dict[str, Any]) -> list[dict[str, Any]]:
        """プロット生成（後方互換）"""
        return self.plot_generator.generate(bible)

    def _extract_spice(self, text: str):
        """尖り要素抽出（後方互換）"""
        return self.episode_rewriter.extract_spice(text)

    def _inject_spice_markers(self, text: str, spice_elements):
        """マーカー注入（後方接続）"""
        return self.episode_rewriter.inject_markers(text, spice_elements)

    def _build_rewrite_prompt(self, content: str, improvements: list[str], spice_elements):
        """リライトプロンプト構築（後方互換）"""
        return self.episode_rewriter.build_prompt(content, improvements, spice_elements)
def create_series(
    engine,
    genre: str,
    target_episodes: int = 8,
    progress_callback: Optional[callable] = None,
) -> EasyModePipeline:
    """シリーズ作成エントリーポイント"""
    settings = get_settings()
    config = PipelineConfig(
        genre=genre,
        target_episodes=target_episodes,
        progress_callback=progress_callback,
        context_window=settings.context_window_target_ratio * 128000,  # Approximate
        context_window_min_reserve=settings.context_window_min_reserve,
    )
    return EasyModePipeline(engine, config)