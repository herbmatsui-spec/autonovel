"""感情状態キャッシュ Week 2: ルールエンジンパッケージ。

プロットイベント定義 → 感情変化ルール適用 → ベースラインベクトル自動生成 →
Vector/Graph/Log への永続化を担う。
"""
from src.rules.plot_events import PlotEvent, PlotEventType, Role
from src.rules.emotional_rules import EmotionalRule, PlotContext
from src.rules.conditions import condition_registry
from src.rules.rule_loader import RuleLoader
from src.rules.state_machine import EmotionalStateMachine
from src.rules.engine import RuleEngine

__all__ = [
    "PlotEvent",
    "PlotEventType",
    "Role",
    "EmotionalRule",
    "PlotContext",
    "condition_registry",
    "RuleLoader",
    "EmotionalStateMachine",
    "RuleEngine",
]
