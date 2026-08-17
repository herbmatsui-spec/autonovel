"""
かんたんモード パイプライン（オーケストレーション専用）
ジャンル選択のみで企画〜完結まで全自動生成
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.core.async_utils import limit_concurrency
from src.core.exceptions import (
    BibleGenerationError,
    EpisodeAuditError,
    EpisodeRewriteError,
    EpisodeWritingError,
    PlotGenerationError,
    SeriesFinalizationError,
)
from src.easy_mode.bible_generator import BibleGenerator
from src.easy_mode.episode_auditor import EpisodeAuditor
from src.easy_mode.episode_rewriter import EpisodeRewriter
from src.easy_mode.episode_writer import EpisodeWriter
from src.easy_mode.models import EpisodeResult, PipelineConfig, RetryConfig, SeriesResult
from src.easy_mode.plot_generator import PlotGenerator
from src.easy_mode.progress_reporter import ProgressReporter
from src.easy_mode.series_finalizer import SeriesFinalizer
from src.presets.loader import load_preset

import tiktoken

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

        # キャンセル伝播
        self._submodules = [
            self.bible_generator,
            self.plot_generator,
            self.episode_writer,
            self.episode_auditor,
            self.episode_rewriter,
            self.series_finalizer,
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
                    self._generate_episode(ep_num, bible, plot_outline, episodes)
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
                total_episodes=config.target_episodes,
                episodes=episodes,
                bible=bible,
                plot_outline=plot_outline,
                metadata=finalize_data,
            )

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self._cancelled = False
            raise

    async def _generate_episode(
        self,
        ep_num: int,
        bible: dict[str, Any],
        plot_outline: list[dict[str, Any]],
        previous_episodes: list[EpisodeResult],
    ) -> EpisodeResult:
        """1話生成（執筆→監査→リライト）"""
        plot = plot_outline[ep_num - 1]

        # 前話までの要約作成
        prev_context = self._build_prev_context(previous_episodes)

        # 執筆
        content = await self.episode_writer.write(ep_num, bible, plot, prev_context)

        # 監査
        audit_result = await self.episode_auditor.audit(
            content, bible, plot, ep_num, self.config.genre
        )

        # リライト（SpiceGuard付き）
        final_content = content
        rewrite_count = 0
        spice_elements = []

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

    def _build_prev_context(self, episodes: list[EpisodeResult]) -> str:
        """前話までの要約文脈構築（トークンベース）"""
        if not episodes:
            return "（第1話のため前話なし）"

        # トークンエンコーダーを初期化
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # 利用可能なトークン数を計算（コンテキストウィンドウから予約領域を差し引く）
        max_tokens = self.config.context_window - self.config.context_window_min_reserve
        
        summaries = []
        tokens_used = 0
        
        # 直近3話から逆順で処理（新しい話から古い話へ）
        for ep in reversed(episodes[-3:]):
            # エピソードの要約テキストを作成
            summary_text = f"第{ep.episode_num}話: {ep.title} - "
            
            # エンコードしてトークン数を計算
            summary_tokens = len(encoding.encode(summary_text))
            
            # 残りトークンで利用可能なコンテンツ長を計算
            remaining_tokens = max_tokens - tokens_used - summary_tokens
            if remaining_tokens <= 0:
                # トークンが足りない場合はこの話をスキップ
                continue
                
            # コンテンツをトークンベースで切り捨て
            content_tokens = encoding.encode(ep.content)
            if len(content_tokens) > remaining_tokens:
                # トークン制限内で切り捨て
                truncated_tokens = content_tokens[:remaining_tokens]
                truncated_content = encoding.decode(truncated_tokens)
            else:
                truncated_content = ep.content
                
            # 最終的な要約テキストを作成
            final_summary = f"{summary_text}{truncated_content}..."
            
            # 実際のトークン数を再計算
            final_tokens = len(encoding.encode(final_summary))
            if tokens_used + final_tokens > max_tokens:
                # トークンオーバーならこの話をスキップ
                continue
                
            summaries.insert(0, final_summary)  # 順序を保持するため先頭に挿入
            tokens_used += final_tokens
            
            # トークン制限に達したらループを抜ける
            if tokens_used >= max_tokens * 0.9:  # 90%で余裕を持たせる
                break

        return "\n\n".join(summaries)

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
    config = PipelineConfig(
        genre=genre, target_episodes=target_episodes, progress_callback=progress_callback
    )
    return EasyModePipeline(engine, config)