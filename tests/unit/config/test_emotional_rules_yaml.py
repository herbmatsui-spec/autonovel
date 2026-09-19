"""Step 3: ルールセット YAML 定義ファイルテスト。"""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionType
from src.rules.conditions import condition_registry
from src.rules.rule_loader import DEFAULT_RULES_PATH, RuleLoader
from src.rules.plot_events import PlotEventType, Role


class TestEmotionalRulesYaml:
    """config/emotional_rules.yaml のロードテスト。"""

    def test_yaml_loads_all_rules(self):
        """YAML から全ルールがロードされる。"""
        loader = RuleLoader()
        rules = loader.load_rules(DEFAULT_RULES_PATH)
        assert len(rules) >= 2  # 計画書サンプルの betrayal, rescue を含む

        event_types = {r.event_type for r in rules}
        assert PlotEventType.BETRAYAL in event_types
        assert PlotEventType.RESCUE in event_types

    def test_betrayal_rule_deltas(self):
        """裏切りルールの感情変化量が計画書通り。"""
        loader = RuleLoader()
        rules = loader.load_rules(DEFAULT_RULES_PATH)
        betrayal = next(r for r in rules if r.event_type == PlotEventType.BETRAYAL)
        assert betrayal.source_role == Role.VICTIM
        assert betrayal.target_role == Role.PERPETRATOR
        assert betrayal.emotion_deltas[EmotionType.AFFECTION] == -0.6
        assert betrayal.emotion_deltas[EmotionType.TENSION] == 0.8
        assert betrayal.emotion_deltas[EmotionType.FEAR] == 0.5
        assert betrayal.emotion_deltas[EmotionType.TRUST] == -0.7
        assert betrayal.decay_per_episode == 0.1

    def test_rescue_rule_deltas(self):
        """救出ルールの感情変化量が計画書通り。"""
        loader = RuleLoader()
        rules = loader.load_rules(DEFAULT_RULES_PATH)
        rescue = next(r for r in rules if r.event_type == PlotEventType.RESCUE)
        assert rescue.source_role == Role.VICTIM
        assert rescue.target_role == Role.RESCUER
        assert rescue.emotion_deltas[EmotionType.AFFECTION] == 0.4
        assert rescue.emotion_deltas[EmotionType.TRUST] == 0.5
        assert rescue.emotion_deltas[EmotionType.TENSION] == -0.3
        assert rescue.decay_per_episode == 0.05

    def test_condition_resolved_from_registry(self):
        """条件関数がレジストリから解決される (eval 不使用)。"""
        loader = RuleLoader()
        rules = loader.load_rules(DEFAULT_RULES_PATH)
        conditioned = [r for r in rules if r.condition is not None]
        assert len(conditioned) >= 1
        # 条件付きルールが評価可能
        from src.rules.emotional_rules import PlotContext
        for rule in conditioned:
            result = rule.evaluate(PlotContext(episode=1, previous_tension=0.9))
            assert isinstance(result, bool)

    def test_missing_file_raises(self):
        """存在しないファイルは FileNotFoundError。"""
        loader = RuleLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_rules("nonexistent_rules.yaml")
