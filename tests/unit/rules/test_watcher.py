"""Step 17: プロットイベント監視・再計算テスト。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.rules.rule_loader import (
    DEFAULT_EVENTS_PATH,
    DEFAULT_RULES_PATH,
    RuleLoader,
    parse_episode_events,
)
from src.rules.watcher import recompute_from_episode
from src.stores.event_log import EventLogStore
from src.stores.graph_store import InMemoryGraphStore


class TestRecomputeFromEpisode:
    """recompute_from_episode テスト。"""

    def test_recompute_from_episode(self, tmp_path):
        """指定エピソードからの再計算。"""
        log_path = str(tmp_path / "emotional_events.jsonl")
        # 事前に ep14 を処理済みの状態を作る
        from src.rules.engine import RuleEngine
        from src.rules.state_machine import EmotionalStateMachine

        rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        events_by_ep = parse_episode_events(DEFAULT_EVENTS_PATH)
        engine.process_episode(14, events_by_ep[14])
        log_store = EventLogStore(log_path)
        engine.persist_results(None, None, log_store, episode=14)

        # ep15 から再計算
        result = recompute_from_episode(
            start_ep=15,
            log_path=log_path,
        )

        assert result["episodes_processed"] == [15, 16]
        assert result["num_events"] == 2
        assert "final_vector" in result

    def test_recompute_from_beginning(self, tmp_path):
        """最初からの再計算 (履歴なし)。"""
        log_path = str(tmp_path / "emotional_events.jsonl")
        result = recompute_from_episode(
            start_ep=1,
            log_path=log_path,
        )
        # ep1 は存在しないため ep14 以降が処理される
        assert result["episodes_processed"] == [14, 15, 16]

    def test_recompute_with_graph_store(self, tmp_path):
        """GraphStore との連携。"""
        log_path = str(tmp_path / "emotional_events.jsonl")
        graph_store = InMemoryGraphStore()
        result = recompute_from_episode(
            start_ep=14,
            log_path=log_path,
            graph_store=graph_store,
        )
        assert len(result["episodes_processed"]) == 3
        # Graph にエッジ蓄積
        edges = graph_store.get_all_edges()
        assert ("A", "B") in edges

    def test_recompute_writes_log(self, tmp_path):
        """再計算結果がログに追記される。"""
        log_path = tmp_path / "emotional_events.jsonl"
        recompute_from_episode(start_ep=14, log_path=str(log_path))
        assert log_path.exists()
        store = EventLogStore(str(log_path))
        assert store.count() > 0

    def test_custom_paths(self, tmp_path):
        """カスタム YAML パスでの再計算。"""
        rules_file = tmp_path / "custom_rules.yaml"
        rules_file.write_text(
            "rules:\n"
            "  - event_type: \"betrayal\"\n"
            "    source_role: \"victim\"\n"
            "    target_role: \"perpetrator\"\n"
            "    emotion_deltas:\n"
            "      affection: -0.5\n"
            "    decay_per_episode: 0.2\n",
            encoding="utf-8",
        )
        events_file = tmp_path / "custom_events.yaml"
        events_file.write_text(
            "episode_1:\n"
            "  - event_id: \"e1\"\n"
            "    event_type: \"betrayal\"\n"
            "    scene: 1\n"
            "    roles:\n"
            "      victim: \"X\"\n"
            "      perpetrator: \"Y\"\n",
            encoding="utf-8",
        )
        result = recompute_from_episode(
            start_ep=1,
            rules_path=str(rules_file),
            events_path=str(events_file),
            log_path=str(tmp_path / "log.jsonl"),
        )
        assert result["episodes_processed"] == [1]
