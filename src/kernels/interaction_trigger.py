"""
kernels/interaction_trigger.py - インタラクショントリガー

本モジュールは二種類のトリガー機構を提供する:
1. InteractionTrigger (Pydantic BaseModel)
   物語状態遷移に連動して発火するドラマチックなトリガー。
   TriggerRegistry で一元管理され、PresetTriggers で利用される。
2. TriggerType / TriggerConfig / InteractionTriggerManager
   UI 層の印象・クリック・スクロール等、読者操作ベースの
   トリガー管理機構。
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List

from pydantic import BaseModel, Field

from .base import KernelState


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


class InteractionTrigger(BaseModel):
    """
    特定の状態条件を満たしたときに発生するドラマチックなトリガー。
    物語状態機械 (NarrativeStateGraph) と連動して発火する。
    """

    trigger_id: str
    name: str
    # 条件判定関数: (current_state, next_state) -> bool
    condition: Callable[[KernelState, KernelState], bool]
    # 発生時の効果: (context, pipeline) -> Any
    action: Callable[[Any, Any], Any]
    # クールダウン期間（シーン数）
    cooldown: int = 3
    # 現在のクールダウン残り
    current_cooldown: int = 0
    # 任意のメタデータ
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TriggerRegistry:
    """
    プリセットされたトリガーを管理し、検知を行うレジストリ。
    """

    def __init__(self) -> None:
        self.triggers: List[InteractionTrigger] = []

    def register(self, trigger: InteractionTrigger) -> None:
        """トリガーを登録"""
        self.triggers.append(trigger)

    def check_triggers(
        self, current_state: KernelState, next_state: KernelState
    ) -> List[InteractionTrigger]:
        """
        現在の状態遷移からトリガーされるイベントを抽出する。
        """
        activated: List[InteractionTrigger] = []
        for trigger in self.triggers:
            if trigger.current_cooldown > 0:
                trigger.current_cooldown -= 1
                continue

            try:
                fired = bool(trigger.condition(current_state, next_state))
            except Exception:
                # 条件関数の例外は握り潰さず、ログ化して継続
                import logging

                logging.getLogger(__name__).warning(
                    "InteractionTrigger '%s' condition raised; skipping",
                    trigger.trigger_id,
                    exc_info=True,
                )
                fired = False

            if fired:
                activated.append(trigger)
                trigger.current_cooldown = trigger.cooldown

        return activated

    def clear(self) -> None:
        """全トリガーをクリア"""
        self.triggers.clear()


class InteractionTriggerManager:
    """
    インタラクショントリガー管理 (UI 層向け)
    """

    def __init__(self) -> None:
        self.triggers: Dict[str, TriggerConfig] = {}
        self.handlers: Dict[str, Callable] = {}
        self._last_trigger_time: Dict[str, float] = {}
        self._activation_counts: Dict[str, int] = {}

    def register_trigger(self, name: str, config: TriggerConfig, handler: Callable) -> None:
        """トリガーを登録"""
        self.triggers[name] = config
        self.handlers[name] = handler
        self._activation_counts[name] = 0

    def should_trigger(self, name: str, context: Dict[str, Any]) -> bool:
        """トリガーを発動すべきか判定"""
        trigger = self.triggers.get(name)
        if not trigger:
            return False

        # 最大発動回数チェック
        if self._activation_counts.get(name, 0) >= trigger.max_activations:
            return False

        # クールダウンチェック
        last_time = self._last_trigger_time.get(name, 0.0)
        if time.time() - last_time < trigger.cooldown_seconds:
            return False

        # 条件チェック
        # ref: 元実装は `actual != expected and actual is None` だったが、
        # 期待値が未設定(None)の場合を除き、期待値と異なる場合は不発火とする。
        for key, expected in trigger.conditions.items():
            actual = context.get(key)
            if expected is None:
                continue
            if actual != expected:
                return False

        self._last_trigger_time[name] = time.time()
        return True

    async def trigger(self, name: str, context: Dict[str, Any]) -> Any:
        """トリガーを発動"""
        if not self.should_trigger(name, context):
            return None

        handler = self.handlers.get(name)
        if handler is None:
            return None

        config = self.triggers.get(name)
        if config is not None:
            self._activation_counts[name] = self._activation_counts.get(name, 0) + 1

        # ハンドラが coroutine関数か否かを安全に判定して呼び分ける。
        # 注意: handler() でインスタンス化する元実装は、handler がクラスの
        # 場合に意図せずコンストラクタを起動してしまうバグがあった。
        import inspect

        if inspect.iscoroutinefunction(handler):
            return await handler(context)
        return handler(context)

    def reset(self) -> None:
        """リセット"""
        self._last_trigger_time.clear()
        self._activation_counts.clear()
