"""
kernels/pipeline.py - パイプライン管理
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineResult:
    """パイプライン結果"""

    status: PipelineStatus = PipelineStatus.PENDING
    data: Dict[str, Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class Stage:
    """パイプラインステージ"""

    def __init__(self, name: str, func: Callable, condition: Optional[Callable] = None):
        self.name = name
        self.func = func
        self.condition = condition

    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.condition and not self.condition(data):
            return data
        return await self.func(data)


class PipelineManager:
    """
    パイプライン管理
    """

    def __init__(self, max_stages: int = 10):
        self.max_stages = max_stages
        self.stages: List[Stage] = []
        self.results: Dict[str, PipelineResult] = {}
        self._current_index = 0

    def add_stage(self, name: str, func: Callable, condition: Optional[Callable] = None) -> None:
        """ステージを追加"""
        stage = Stage(name, func, condition)
        self.stages.append(stage)

    async def run(self, initial_data: Dict[str, Any]) -> PipelineResult:
        """パイプラインを実行"""
        # パイプライン結果を初期化
        result = PipelineResult(status=PipelineStatus.RUNNING, data=initial_data)
        start_time = time.time()
        result.data = initial_data.copy()

        try:
            # ステージを順に実行
            for stage in self.stages:
                result = await stage.execute(result.data)
                self._current_index += 1

            # 成功時：完了状態を設定
            result.status = PipelineStatus.COMPLETED
            result.execution_time = time.time() - start_time
        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)

        return result

    def get_progress(self) -> Dict[str, Any]:
        """進捗を取得"""
        return {
            "current_stage": self._current_index,
            "total_stages": len(self.stages),
            "completion_rate": self._current_index / len(self.stages) if self.stages else 0,
        }

    def clear(self) -> None:
        """クリア"""
        self.stages.clear()
        self._current_index = 0
