"""
kernels/base.py - 基本機能の基礎クラス
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class KernelState(Enum):
    """カーネルの状態を表す列挙型"""
    INITIALIZED = "initialized"
    ACTIVE = "active"
    ERROR = "error"
    STOPPED = "stopped"
    PAUSED = "paused"


@dataclass
class KernelContext:
    """カーネルのコンテキスト情報"""
    session_id: str
    user_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0


class KernelBase(ABC):
    """
    全てのカーネルクラスの基底クラス
    """

    def __init__(self, context: Optional[KernelContext] = None):
        self.context = context or KernelContext(
            session_id="default",
            user_id="anonymous",
            metadata={}
        )
        self._state = KernelState.INITIALIZED
        self._lock = asyncio.Lock()

    @property
    def state(self) -> KernelState:
        return self._state

    @abstractmethod
    async def initialize(self) -> bool:
        """カーネルを初期化"""
        pass

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """カーネルの主処理を実行"""
        pass

    async def cleanup(self) -> None:
        """クリーンアップ処理"""
        self._state = KernelState.STOPPED

    def set_state(self, state: KernelState) -> None:
        """状態を設定"""
        self._state = state

    def validate_context(self) -> bool:
        """コンテキストの妥当性を検証"""
        return (
            self.context.session_id is not None
            and len(self.context.session_id) > 0
        )
