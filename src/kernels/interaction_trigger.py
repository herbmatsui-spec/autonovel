"""
kernels/interaction_trigger.py - インタラクショントリガー
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict


class TriggerType(str, Enum):
    """トリガータイプ"""
    IMPRESSION = "impression"
    CLICK = "click"
    SCROLL = "scroll"
    TIME_BASED = "time_based"
    INTERACTION = "interaction"


@dataclass
class TriggerConfig:
    """トリガー設定"""
    trigger_type: TriggerType
    conditions: Dict[str, Any]
    cooldown_seconds: float = 30.0
    max_activations: int = 3


class InteractionTriggerManager:
    """
    インタラクショントリガー管理
    """

    def __init__(self):
        self.triggers: Dict[str, TriggerConfig] = {}
        self.handlers: Dict[str, Callable] = {}
        self._last_trigger_time: Dict[str, float] = {}

    def register_trigger(self, name: str, config: TriggerConfig, handler: Callable) -> None:
        """トリガーを登録"""
        self.triggers[name] = config
        self.handlers[name] = handler

    def should_trigger(self, name: str, context: Dict[str, Any]) -> bool:
        """トリガーを発動すべきか判定"""
        import time
        trigger = self.triggers.get(name)
        if not trigger:
            return False

        # クールダウンチェック
        last_time = self._last_trigger_time.get(name, 0)
        if time.time() - last_time < trigger.cooldown_seconds:
            return False

        # 条件チェック
        for key, expected in trigger.conditions.items():
            actual = context.get(key)
            if actual != expected and actual is None:
                return False

        self._last_trigger_time[name] = time.time()
        return True

    async def trigger(self, name: str, context: Dict[str, Any]) -> Any:
        """トリガーを発動"""
        if self.should_trigger(name, context):
            handler = self.handlers.get(name)
            if handler:
                return await handler(context) if hasattr(handler, '__call__') and hasattr(handler(), '__await__') else handler(context)
        return None

    def reset(self) -> None:
        """リセット"""
        self._last_trigger_time.clear()


