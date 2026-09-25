"""Step 5: 条件関数レジストリテスト。"""
from __future__ import annotations

import pytest

from src.rules.conditions import condition_registry
from src.rules.emotional_rules import PlotContext


class TestConditionRegistry:
    """条件関数テスト。"""

    def test_relationship_above(self):
        """relationship_above の動作確認。"""
        func = condition_registry.create("relationship_above", threshold=0.5)
        assert func(PlotContext(episode=1, relationship_level=0.6)) is True
        assert func(PlotContext(episode=1, relationship_level=0.5)) is True
        assert func(PlotContext(episode=1, relationship_level=0.4)) is False

    def test_tension_above(self):
        """tension_above の動作確認。"""
        func = condition_registry.create("tension_above", threshold=0.6)
        assert func(PlotContext(episode=1, previous_tension=0.7)) is True
        assert func(PlotContext(episode=1, previous_tension=0.5)) is False

    def test_previous_event_was(self):
        """previous_event_was の動作確認。"""
        func = condition_registry.create("previous_event_was", event_type="betrayal")
        ctx_with = PlotContext(episode=1, custom_data={"previous_event_type": "betrayal"})
        ctx_without = PlotContext(episode=1)
        ctx_other = PlotContext(episode=1, custom_data={"previous_event_type": "rescue"})
        assert func(ctx_with) is True
        assert func(ctx_without) is False
        assert func(ctx_other) is False

    def test_custom_flag(self):
        """custom_flag の動作確認。"""
        func = condition_registry.create("custom_flag", flag_name="forced")
        assert func(PlotContext(episode=1, custom_data={"forced": True})) is True
        assert func(PlotContext(episode=1, custom_data={})) is False
        assert func(PlotContext(episode=1, custom_data={"forced": False})) is False

    def test_unknown_condition_raises(self):
        """未登録条件は KeyError。"""
        with pytest.raises(KeyError):
            condition_registry.get("nonexistent_condition")

    def test_register_decorator(self):
        """デコレータでの自動登録。"""

        @condition_registry.register("test_decorator_flag")
        def test_condition(ctx):
            return ctx.relationship_level > 0.9

        assert condition_registry.has("test_decorator_flag")
        func = condition_registry.get("test_decorator_flag")
        assert func(PlotContext(episode=1, relationship_level=0.95)) is True

    def test_all_planned_conditions_registered(self):
        """計画書に定義された条件関数が全て登録されている。"""
        for name in ("relationship_above", "tension_above", "previous_event_was", "custom_flag"):
            assert condition_registry.has(name), f"{name} is not registered"
