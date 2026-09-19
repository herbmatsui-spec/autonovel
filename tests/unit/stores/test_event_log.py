"""Step 12: EventLog ストアテスト (JSONL append-only)。"""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionalSignal, EmotionType
from src.rules.state_machine import EmotionalStateMachine
from src.stores.event_log import EventLogStore, DEFAULT_LOG_PATH


def _signal(source="A", target="B", emotion=EmotionType.AFFECTION, value=0.5, episode="ep14"):
    return EmotionalSignal(
        source=source, target=target, emotion_type=emotion, value=value,
        confidence=1.0, evidence_span="test", episode_id=episode, cause="betrayal",
    )


class TestEventLogStore:
    """EventLogStore テスト。"""

    def test_append_and_query(self, tmp_path):
        """追加とクエリ。"""
        store = EventLogStore(str(tmp_path / "events.jsonl"))
        store.append(_signal(episode="ep14"))
        store.append(_signal(episode="ep15"))
        store.append(_signal(source="C", target="D", episode="ep14"))

        # ペア指定
        result = store.query(pair=("A", "B"))
        assert len(result) == 2
        assert all(s.source == "A" and s.target == "B" for s in result)

        # エピソード範囲指定
        result = store.query(pair=("A", "B"), from_ep=15, to_ep=15)
        assert len(result) == 1
        assert result[0].episode_id == "ep15"

        # 全件
        assert store.query() .__len__() == 3
        assert store.count() == 3

    def test_jsonl_format(self, tmp_path):
        """1行1イベントの JSONL 形式。"""
        log_path = tmp_path / "events.jsonl"
        store = EventLogStore(str(log_path))
        store.append(_signal())
        store.append(_signal())

        content = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(content) == 2
        import json
        for line in content:
            data = json.loads(line)
            assert "source" in data
            assert "emotion_type" in data
            assert data["emotion_type"] == "affection"

    def test_replay_to_episode(self, tmp_path):
        """全再生で状態復元。"""
        store = EventLogStore(str(tmp_path / "events.jsonl"))
        store.append(_signal(emotion=EmotionType.AFFECTION, value=-0.6, episode="ep14"))
        store.append(_signal(emotion=EmotionType.TENSION, value=0.8, episode="ep14"))
        store.append(_signal(emotion=EmotionType.TRUST, value=0.5, episode="ep15"))

        # ep14 まで復元
        sm = store.replay_to_episode(14)
        assert sm.get_value("A", "B", EmotionType.AFFECTION) == -0.6
        assert sm.get_value("A", "B", EmotionType.TENSION) == 0.8
        assert sm.get_value("A", "B", EmotionType.TRUST) == 0.0  # ep15 は未適用

        # ep15 まで復元
        sm_full = store.replay_to_episode(15)
        assert sm_full.get_value("A", "B", EmotionType.TRUST) == 0.5

    def test_replay_matches_snapshot(self, tmp_path):
        """リプレイ結果がスナップショットと一致。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, -0.6)
        sm.apply_delta("A", "B", EmotionType.TENSION, 0.8)

        store = EventLogStore(str(tmp_path / "events.jsonl"))
        store.append(_signal(emotion=EmotionType.AFFECTION, value=-0.6, episode="ep14"))
        store.append(_signal(emotion=EmotionType.TENSION, value=0.8, episode="ep14"))

        replayed = store.replay_to_episode(14)
        assert replayed.snapshot() == sm.snapshot()

    def test_empty_file(self, tmp_path):
        """空ファイルの扱い。"""
        store = EventLogStore(str(tmp_path / "events.jsonl"))
        assert store.count() == 0
        assert store.query() == []
        assert store.replay_to_episode(10).snapshot() == {}

    def test_malformed_line_skipped(self, tmp_path):
        """不正行はスキップ。"""
        log_path = tmp_path / "events.jsonl"
        log_path.write_text(
            '{"source": "A", "target": "B", "emotion_type": "affection", "value": 0.5, '
            '"confidence": 1.0, "evidence_span": "t", "episode_id": "ep1"}\n'
            "not valid json\n",
            encoding="utf-8",
        )
        store = EventLogStore(str(log_path))
        assert store.count() == 1

    def test_default_path(self):
        """デフォルトパスは data/emotional_events.jsonl。"""
        assert DEFAULT_LOG_PATH.endswith("emotional_events.jsonl")
        assert "data" in DEFAULT_LOG_PATH
