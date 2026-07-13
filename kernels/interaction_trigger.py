from typing import Any, Callable, List

from pydantic import BaseModel

from kernels.base import KernelState


class InteractionTrigger(BaseModel):
    """
    特定の状態条件を満たしたときに発生するドラマチックなトリガー。
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

class TriggerRegistry:
    """
    プリセットされたトリガーを管理し、検知を行うレジストリ。
    """
    def __init__(self):
        self.triggers: List[InteractionTrigger] = []

    def register(self, trigger: InteractionTrigger):
        self.triggers.append(trigger)

    def check_triggers(self, current_state: KernelState, next_state: KernelState) -> List[InteractionTrigger]:
        """
        現在の状態遷移からトリガーされるイベントを抽出する。
        """
        activated = []
        for trigger in self.triggers:
            if trigger.current_cooldown > 0:
                trigger.current_cooldown -= 1
                continue

            if trigger.condition(current_state, next_state):
                activated.append(trigger)
                trigger.current_cooldown = trigger.cooldown

        # 優先順位に基づいたソート (ここでは単純に定義順とするが、必要に応じて優先度プロパティを追加)
        return activated

