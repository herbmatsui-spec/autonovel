"""
進捗報告ユーティリティ
"""

from __future__ import annotations

<<<<<<< ours
from typing import Callable, Optional
=======
from typing import Any, Callable, Optional
>>>>>>> theirs


class ProgressReporter:
    """進捗報告"""

    def __init__(self, callback: Optional[Callable[[str, int, int], None]] = None):
        self.callback = callback

    async def report(self, stage: str, current: int, total: int):
        """進捗コールバック呼び出し"""
        if self.callback:
            self.callback(stage, current, total)


def create_progress_reporter(callback: Optional[Callable[[str, int, int], None]] = None) -> ProgressReporter:
    """進捗報告ファクトリ"""
<<<<<<< ours
    return ProgressReporter(callback)
=======
    return ProgressReporter(callback)
>>>>>>> theirs
