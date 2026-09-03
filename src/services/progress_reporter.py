"""
進捗報告アダプタ
FullAutoWorkflow と EasyModePipeline の異なる進捗APIを統一
"""

from __future__ import annotations

from typing import Any, Protocol


class ProgressReporterProtocol(Protocol):
    """FullAutoWorkflow 風の進捗レポーター (StatusReporter 互換)"""

    def update_progress(
        self, current: int, total: int, message: str = "", sub_message: str = ""
    ) -> None: ...

    def report(self, message: str, level: str = "info") -> None: ...

    @property
    def state(self) -> Any: ...


class ProgressCallbackProtocol(Protocol):
    """EasyModePipeline 風の進捗コールバック"""

    def __call__(self, stage: str, current: int, total: int) -> None: ...


class UnifiedProgressReporter:
    """
    統一進捗レポーター
    内部では FullAuto 風 API を使用し、EasyMode 風コールバックもサポート
    """

    def __init__(
        self,
        reporter: ProgressReporterProtocol | None = None,
        easy_callback: ProgressCallbackProtocol | None = None,
    ):
        self._reporter = reporter
        self._easy_callback = easy_callback
        self._current_stage = ""
        self._stage_progress = 0
        self._total_stages = 4  # デフォルト: 企画/プロット/執筆/完結

    def update_progress(
        self, current: int, total: int, message: str = "", sub_message: str = ""
    ) -> None:
        """FullAuto 風 API"""
        if self._reporter:
            self._reporter.update_progress(current, total, message, sub_message)

        # EasyMode 風コールバックにも通知 (stage 推定)
        if self._easy_callback:
            stage = self._estimate_stage(current, total)
            self._easy_callback(stage, current, total)

    def report(self, message: str, level: str = "info") -> None:
        """ログ報告"""
        if self._reporter:
            self._reporter.report(message, level)

    def report_stage(self, stage: str, current: int, total: int, message: str = "") -> None:
        """ステージ明示的報告 (内部推奨)"""
        self._current_stage = stage
        self._stage_progress = current
        self._total_stages = total

        if self._reporter:
            self._reporter.update_progress(current, total, message, stage)

        if self._easy_callback:
            self._easy_callback(stage, current, total)

    def _estimate_stage(self, current: int, total: int) -> str:
        """進捗からステージ推定"""
        if total <= 0:
            return "unknown"

        ratio = current / total
        if ratio <= 0.25:
            return "bible"
        elif ratio <= 0.5:
            return "plot"
        elif ratio <= 0.75:
            return "writing"
        else:
            return "finalizing"

    @property
    def state(self) -> Any:
        """State アクセス (FullAuto 互換)"""
        if self._reporter:
            return self._reporter.state
        return None

    def should_stop(self) -> bool:
        """停止判定"""
        if self._reporter and hasattr(self._reporter.state, "should_stop"):
            return self._reporter.state.should_stop()
        return False


def create_progress_adapter(
    reporter: ProgressReporterProtocol | None = None,
    easy_callback: ProgressCallbackProtocol | None = None,
) -> UnifiedProgressReporter:
    """ファクトリ関数"""
    return UnifiedProgressReporter(reporter=reporter, easy_callback=easy_callback)


# 既存 StatusReporter へのアダプタ (互換性維持用)
class StatusReporterAdapter:
    """既存の StatusReporter を UnifiedProgressReporter に適応"""

    def __init__(self, reporter: ProgressReporterProtocol):
        self._reporter = reporter

    def update_progress(
        self, current: int, total: int, message: str = "", sub_message: str = ""
    ) -> None:
        self._reporter.update_progress(current, total, message, sub_message)

    def report(self, message: str, level: str = "info") -> None:
        self._reporter.report(message, level)

    @property
    def state(self) -> Any:
        return self._reporter.state

    def should_stop(self) -> bool:
        if hasattr(self._reporter.state, "should_stop"):
            return self._reporter.state.should_stop()
        return False
