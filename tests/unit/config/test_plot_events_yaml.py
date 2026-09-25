"""Step 6: プロットイベント入力ファイル形式テスト。"""
from __future__ import annotations

import pytest

from src.rules.plot_events import PlotEventType, Role
from src.rules.rule_loader import DEFAULT_EVENTS_PATH, parse_episode_events


class TestPlotEventsYaml:
    """config/plot_events.yaml のパーステスト。"""

    def test_parse_episode_events(self):
        """エピソード別イベントリストのパース。"""
        events = parse_episode_events(DEFAULT_EVENTS_PATH)
        assert 14 in events
        assert 15 in events
        assert 16 in events

        ep14 = events[14]
        assert len(ep14) == 1
        event = ep14[0]
        assert event.event_id == "ep14_betrayal"
        assert event.event_type == PlotEventType.BETRAYAL
        assert event.scene == 3
        assert event.get_character(Role.VICTIM) == "A"
        assert event.get_character(Role.PERPETRATOR) == "B"

    def test_metadata_parsed(self):
        """metadata がパースされる。"""
        events = parse_episode_events(DEFAULT_EVENTS_PATH)
        ep14 = events[14][0]
        assert ep14.metadata.get("witness") == "C"
        assert ep14.metadata.get("relationship_level") == 0.6

    def test_unknown_key_skipped(self, tmp_path):
        """未知のキーはスキップされる。"""
        yaml_file = tmp_path / "events.yaml"
        yaml_file.write_text(
            "episode_1:\n"
            "  - event_id: e1\n"
            "    event_type: rescue\n"
            "    scene: 1\n"
            "    roles: {victim: A}\n"
            "unknown_key:\n"
            "  - event_id: bad\n"
            "    event_type: rescue\n",
            encoding="utf-8",
        )
        events = parse_episode_events(str(yaml_file))
        assert 1 in events
        assert len(events) == 1

    def test_invalid_event_skipped(self, tmp_path):
        """不正なイベントはスキップされる。"""
        yaml_file = tmp_path / "events.yaml"
        yaml_file.write_text(
            "episode_1:\n"
            "  - event_id: e1\n"
            "    event_type: rescue\n"
            "    scene: 1\n"
            "    roles: {victim: A}\n"
            "  - event_type: rescue\n"  # event_id 欠落
            "  - event_id: e2\n"
            "    event_type: unknown_event_type\n"  # 不正タイプ
            "    scene: 2\n",
            encoding="utf-8",
        )
        events = parse_episode_events(str(yaml_file))
        assert len(events[1]) == 1
        assert events[1][0].event_id == "e1"

    def test_missing_file_raises(self):
        """存在しないファイルは FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            parse_episode_events("nonexistent_events.yaml")
