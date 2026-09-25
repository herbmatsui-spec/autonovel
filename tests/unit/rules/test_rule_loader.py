"""Step 4: ルールローダーテスト。"""
from __future__ import annotations

import pytest

from src.rules.rule_loader import (
    DEFAULT_EVENTS_PATH,
    DEFAULT_RULES_PATH,
    RuleLoader,
    _extract_episode_number,
    parse_episode_events,
)


class TestRuleLoader:
    """RuleLoader テスト。"""

    def test_load_rules_with_conditions(self):
        """条件付きルールを含むロード。"""
        loader = RuleLoader()
        rules = loader.load_rules(DEFAULT_RULES_PATH)
        assert len(rules) > 0
        # 全ルールが有効な構造を持つ
        for rule in rules:
            assert rule.emotion_deltas, f"Rule {rule.rule_id} has no deltas"
            assert 0.0 <= rule.decay_per_episode <= 1.0

    def test_load_rules_custom_yaml(self, tmp_path):
        """カスタム YAML からのロード。"""
        yaml_file = tmp_path / "rules.yaml"
        yaml_file.write_text(
            "rules:\n"
            "  - event_type: \"betrayal\"\n"
            "    source_role: \"victim\"\n"
            "    target_role: \"perpetrator\"\n"
            "    emotion_deltas:\n"
            "      affection: -0.5\n"
            "    decay_per_episode: 0.2\n",
            encoding="utf-8",
        )
        loader = RuleLoader()
        rules = loader.load_rules(str(yaml_file))
        assert len(rules) == 1
        assert rules[0].decay_per_episode == 0.2

    def test_load_rules_unknown_condition_unconditional(self, tmp_path):
        """未知の条件名は無条件適用にフォールバック。"""
        yaml_file = tmp_path / "rules.yaml"
        yaml_file.write_text(
            "rules:\n"
            "  - event_type: \"betrayal\"\n"
            "    source_role: \"victim\"\n"
            "    target_role: \"perpetrator\"\n"
            "    emotion_deltas:\n"
            "      affection: -0.5\n"
            "    condition: \"never_registered_cond\"\n",
            encoding="utf-8",
        )
        loader = RuleLoader()
        rules = loader.load_rules(str(yaml_file))
        assert len(rules) == 1
        assert rules[0].condition is None  # デフォルト条件 (常に真)

    def test_load_rules_invalid_rule_skipped(self, tmp_path):
        """不正なルールはスキップ。"""
        yaml_file = tmp_path / "rules.yaml"
        yaml_file.write_text(
            "rules:\n"
            "  - event_type: \"betrayal\"\n"
            "    source_role: \"victim\"\n"
            "    target_role: \"perpetrator\"\n"
            "    emotion_deltas:\n"
            "      affection: -0.5\n"
            "  - source_role: \"victim\"\n"  # event_type 欠落
            "    emotion_deltas: {}\n"
            "  - event_type: \"nonexistent_type\"\n"  # 不正タイプ
            "    source_role: \"victim\"\n"
            "    target_role: \"perpetrator\"\n"
            "    emotion_deltas: {}\n",
            encoding="utf-8",
        )
        loader = RuleLoader()
        rules = loader.load_rules(str(yaml_file))
        assert len(rules) == 1

    def test_extract_episode_number(self):
        """エピソード番号抽出。"""
        assert _extract_episode_number("episode_14") == 14
        assert _extract_episode_number("episode_1") == 1
        assert _extract_episode_number("ep14") is None
        assert _extract_episode_number("unknown") is None

    def test_parse_events_defaults(self):
        """デフォルトパスでのイベントパース。"""
        events = parse_episode_events(DEFAULT_EVENTS_PATH)
        assert len(events) >= 3
