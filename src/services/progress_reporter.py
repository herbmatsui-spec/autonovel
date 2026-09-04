"""
進捗報告アダプタ

統合パイプラインで StatusReporter をラップし、共通の update_progress / report /
state / should_stop インターフェースを提供する。
"""

from __future__ import annotations

from typing import Any


class ProgressReporterAdapter:
    """
    StatusReporter を ProgressReporterAdapter でラップし、Pipeline 内部から
    共通の update_progress / report / state / should_stop インターフェースで扱う。

    is_easy_mode は呼び出し側 (Workflow) の文脈を保持するためのフラグで、
    現在は挙動に影響しないが、将来的な差別化のために保持する。
    """

    def __init__(self, reporter: Any, is_easy_mode: bool = False):
        self._reporter = reporter
        self._is_easy_mode = is_easy_mode

    def update_progress(
        self, current: int, total: int, message: str = "", sub_message: str = ""
    ) -> None:
        """FullAuto 風 API"""
        if hasattr(self._reporter, "update_progress"):
            self._reporter.update_progress(current, total, message, sub_message)

    def report(self, message: str, level: str = "info") -> None:
        """ログ報告"""
        if hasattr(self._reporter, "report"):
            self._reporter.report(message, level)

    @property
    def state(self) -> Any:
        """State アクセス"""
        if hasattr(self._reporter, "state"):
            return self._reporter.state
        return None

    def should_stop(self) -> bool:
        """停止判定"""
        if hasattr(self._reporter, "state") and hasattr(self._reporter.state, "should_stop"):
            return self._reporter.state.should_stop()
        return False