"""Step 20: 開発者向けデバッグCLIテスト。"""
from __future__ import annotations

import json

import pytest

from src.pipeline.emotional_residue import EmotionalSignal, EmotionType
from src.rules.debug_cli import main, show_graph_path, show_log, show_state
from src.stores.event_log import EventLogStore


@pytest.fixture
def log_path(tmp_path):
    """テスト用イベントログを作成する。"""
    path = tmp_path / "emotional_events.jsonl"
    store = EventLogStore(str(path))
    store.append(EmotionalSignal("A", "B", EmotionType.AFFECTION, -0.6, 1.0, "e1", "ep14", "betrayal"))
    store.append(EmotionalSignal("A", "B", EmotionType.TENSION, 0.8, 1.0, "e1", "ep14", "betrayal"))
    store.append(EmotionalSignal("A", "B", EmotionType.TRUST, 0.5, 1.0, "e2", "ep15", "rescue"))
    store.append(EmotionalSignal("B", "C", EmotionType.TRUST, 0.3, 1.0, "e3", "ep16", "rescue"))
    return str(path)


class TestShowState:
    """show-state コマンドテスト。"""

    def test_show_state(self, log_path):
        """エピソード時点の状態表示。"""
        result = show_state(15, pair=("A", "B"), log_path=log_path)
        assert "A->B" in result
        assert result["A->B"][EmotionType.AFFECTION.value] == -0.6
        assert result["A->B"][EmotionType.TENSION.value] == 0.8
        assert result["A->B"][EmotionType.TRUST.value] == 0.5

    def test_show_state_all_pairs(self, log_path):
        """全ペア表示。"""
        result = show_state(16, log_path=log_path)
        assert "A->B" in result
        assert "B->C" in result

    def test_show_state_episode_filter(self, log_path):
        """エピソードフィルタ。"""
        result = show_state(14, log_path=log_path)
        assert result["A->B"].get(EmotionType.TRUST.value) is None  # ep15 は未反映

    def test_show_state_cli(self, log_path, capsys):
        """CLI 経由の実行。"""
        ret = main(["show-state", "--episode", "15", "--pair", "A", "B", "--log", log_path])
        assert ret == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "A->B" in data


class TestShowGraphPath:
    """show-graph-path コマンドテスト。"""

    def test_show_graph_path(self, log_path):
        """因果パス表示 (同一ペアの複数エッジは最新が使用される)。"""
        result = show_graph_path("A", "B", log_path=log_path)
        assert len(result) == 1
        assert result[0]["from"] == "A"
        assert result[0]["to"] == "B"
        # A->B には ep14 (betrayal) と ep15 (rescue) があるため最新の rescue
        assert result[0]["cause"] == "rescue"
        assert result[0]["episode"] == 15

    def test_show_graph_path_multi_hop(self, log_path):
        """マルチホップパス。"""
        result = show_graph_path("A", "C", max_hops=3, log_path=log_path)
        assert len(result) == 2
        assert result[1]["to"] == "C"

    def test_show_graph_path_cli(self, log_path, capsys):
        """CLI 経由の実行。"""
        ret = main(["show-graph-path", "--source", "A", "--target", "C", "--log", log_path])
        assert ret == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data) == 2


class TestShowLog:
    """show-log コマンドテスト。"""

    def test_show_log(self, log_path):
        """ログ表示。"""
        result = show_log(pair=("A", "B"), log_path=log_path)
        assert len(result) == 3
        assert all(e["source"] == "A" for e in result)

    def test_show_log_episode_range(self, log_path):
        """エピソード範囲指定。"""
        result = show_log(pair=("A", "B"), from_ep=15, to_ep=15, log_path=log_path)
        assert len(result) == 1
        assert result[0]["episode_id"] == "ep15"

    def test_show_log_cli(self, log_path, capsys):
        """CLI 経由の実行。"""
        ret = main(["show-log", "--pair", "A", "B", "--from", "10", "--to", "15",
                    "--log", log_path])
        assert ret == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert len(data) == 3

    def test_invalid_command(self, capsys):
        """不正コマンドは 1 を返す。"""
        ret = main([])
        assert ret == 1
