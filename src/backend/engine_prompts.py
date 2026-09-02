from typing import Any


class FastPlotScreenResult:
    def __init__(self, plot_data: dict[str, Any]) -> None:
        self.plot_data = plot_data


class AbilityAuditResult:
    def __init__(self, strengths: list[str], weaknesses: list[str]) -> None:
        self.strengths = strengths
        self.weaknesses = weaknesses


class DeAIAuditResult:
    def __init__(self, issues: list[str], proposed_rules: list[str]) -> None:
        self.issues = issues
        self.proposed_rules = proposed_rules


class DeAIProposedRules:
    def __init__(self, rules: list[str]) -> None:
        self.rules = rules


def get_rule_set(rule_type: str) -> str:
    # Return a sample rule set for testing
    return """
Rule 1: Show, don't tell
Rule 2: Keep dialogue concise
Rule 3: Maintain consistent character voice
"""


# 実際のプロンプト管理クラスは prompts/manager.py で定義されている。
# テスト・既存コードとの互換性のため、ここから再エクスポートする。
from prompts.manager import PromptManager  # noqa: E402,F401
