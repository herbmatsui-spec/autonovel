from typing import Any, Dict, List


class FastPlotScreenResult:
    def __init__(self, plot_data: Dict[str, Any]) -> None:
        self.plot_data = plot_data

class AbilityAuditResult:
    def __init__(self, strengths: List[str], weaknesses: List[str]) -> None:
        self.strengths = strengths
        self.weaknesses = weaknesses

class DeAIAuditResult:
    def __init__(self, issues: List[str], proposed_rules: List[str]) -> None:
        self.issues = issues
        self.proposed_rules = proposed_rules

class DeAIProposedRules:
    def __init__(self, rules: List[str]) -> None:
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


