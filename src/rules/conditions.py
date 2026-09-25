"""条件関数レジストリ (Week 2 Step 5)。

ルールの適用条件として使用できる事前定義関数を提供する。
YAML から文字列式を eval せず、このレジストリ経由で関数を参照する。
"""
from __future__ import annotations

from typing import Callable, Dict

from src.rules.emotional_rules import PlotContext

ConditionFunc = Callable[[PlotContext], bool]


class ConditionRegistry:
    """条件関数レジストリ。

    ``@condition_registry.register("name")`` でデコレートした関数を
    文字列名で参照可能にする。
    """

    def __init__(self) -> None:
        self._conditions: Dict[str, ConditionFunc] = {}

    def register(self, name: str) -> Callable[[ConditionFunc], ConditionFunc]:
        """条件関数を名前付きで登録するデコレータ。"""

        def decorator(func: ConditionFunc) -> ConditionFunc:
            self._conditions[name] = func
            return func

        return decorator

    def get(self, name: str) -> ConditionFunc:
        """名前から条件関数を取得 (未登録なら KeyError)。"""
        if name not in self._conditions:
            raise KeyError(f"Unknown condition: {name!r}")
        return self._conditions[name]

    def has(self, name: str) -> bool:
        """名前が登録済みか判定。"""
        return name in self._conditions

    def names(self) -> list[str]:
        """登録済み条件名一覧。"""
        return sorted(self._conditions.keys())

    def create(self, name: str, **params) -> ConditionFunc:
        """名前とパラメータから部分適用済み条件関数を生成。

        例: ``create("relationship_above", threshold=0.5)``
        関数がパラメータを受け取らない場合はそのまま返す。
        """
        func = self.get(name)
        try:
            # 部分適用を試みる (パラメータを取る関数向け)
            return lambda ctx: func(ctx, **params)  # type: ignore[call-arg]
        except TypeError:
            return func


# モジュールレベルのシングルインスタンス
condition_registry = ConditionRegistry()


@condition_registry.register("relationship_above")
def relationship_above(ctx: PlotContext, threshold: float = 0.5) -> bool:
    """関係レベルが閾値以上か判定。"""
    return ctx.relationship_level >= threshold


@condition_registry.register("tension_above")
def tension_above(ctx: PlotContext, threshold: float = 0.5) -> bool:
    """直前の緊張度が閾値以上か判定。"""
    return ctx.previous_tension >= threshold


@condition_registry.register("previous_event_was")
def previous_event_was(ctx: PlotContext, event_type: str = "") -> bool:
    """直前のイベントが指定タイプだったか判定。"""
    # custom_data["previous_event_type"] にエンジンが記録する前提
    prev = ctx.custom_data.get("previous_event_type")
    if prev is None:
        return False
    if hasattr(prev, "value"):
        prev = prev.value
    return str(prev).lower() == str(event_type).lower()


@condition_registry.register("custom_flag")
def custom_flag(ctx: PlotContext, flag_name: str = "") -> bool:
    """カスタムフラグが立っているか判定。"""
    return bool(ctx.custom_data.get(flag_name))


__all__ = [
    "ConditionRegistry",
    "ConditionFunc",
    "condition_registry",
    "relationship_above",
    "tension_above",
    "previous_event_was",
    "custom_flag",
]
