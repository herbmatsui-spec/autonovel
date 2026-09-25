"""Step 1: プロットイベント型定義テスト。"""
from __future__ import annotations

import pytest

from src.rules.plot_events import PlotEvent, PlotEventType, Role


class TestPlotEventCreation:
    """PlotEvent 生成テスト。"""

    def test_plot_event_creation(self):
        """基本的なイベント生成。"""
        event = PlotEvent(
            event_id="ep14_betrayal",
            episode=14,
            scene=3,
            event_type=PlotEventType.BETRAYAL,
            roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"},
            metadata={"witness": "C"},
        )
        assert event.event_id == "ep14_betrayal"
        assert event.episode == 14
        assert event.scene == 3
        assert event.event_type == PlotEventType.BETRAYAL
        assert event.get_character(Role.VICTIM) == "A"
        assert event.get_character(Role.PERPETRATOR) == "B"

    def test_event_type_from_string(self):
        """文字列から event_type が自動変換される。"""
        event = PlotEvent(
            event_id="ep1_rescue",
            episode=1,
            scene=1,
            event_type="rescue",
        )
        assert event.event_type == PlotEventType.RESCUE

    def test_all_event_types_exist(self):
        """計画書に定義された全イベントタイプが存在する。"""
        expected = {
            "BETRAYAL", "RESCUE", "CONFESSION", "COMBAT_VICTORY",
            "LOSS_OF_LOVED_ONE", "SECRET_SHARED", "FORCED_COOPERATION",
            "REJECTION", "CUSTOM",
        }
        actual = {e.name for e in PlotEventType}
        assert expected == actual

    def test_all_roles_exist(self):
        """計画書に定義された全役割が存在する。"""
        expected = {
            "VICTIM", "PERPETRATOR", "RESCUER", "WITNESS", "SHARER",
            "RECEIVER", "PARTICIPANT", "CONFESSOR", "LISTENER",
        }
        actual = {r.name for r in Role}
        assert expected == actual

    def test_get_character_missing_role(self):
        """存在しない役割は None を返す。"""
        event = PlotEvent(
            event_id="e", episode=1, scene=1, event_type="betrayal",
            roles={Role.VICTIM: "A"},
        )
        assert event.get_character(Role.RESCUER) is None

    def test_to_dict_and_from_dict_roundtrip(self):
        """辞書変換の往復テスト。"""
        event = PlotEvent(
            event_id="ep14_betrayal",
            episode=14,
            scene=3,
            event_type=PlotEventType.BETRAYAL,
            roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"},
            metadata={"witness": "C"},
        )
        data = event.to_dict()
        restored = PlotEvent.from_dict({**data, "episode": 14})
        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.get_character(Role.VICTIM) == "A"

    def test_from_dict_unknown_role_fallback(self):
        """未知の役割は PARTICIPANT にフォールバック。"""
        event = PlotEvent.from_dict({
            "event_id": "e",
            "episode": 1,
            "scene": 1,
            "event_type": "betrayal",
            "roles": {"unknown_role": "X"},
        })
        assert event.get_character(Role.PARTICIPANT) == "X"
