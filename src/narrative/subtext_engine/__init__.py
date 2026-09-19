"""
Subtext Engine Package: Deterministic rule-based subtext rewrite engine.
"""

from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import (
    DialogueBlock,
    RewriteResult,
    RewriteRuleModel,
    SubtextContext,
)
from src.narrative.subtext_engine.rules import (
    AddressDistanceRule,
    CausalToIronyRule,
    ComplianceSubvertRule,
    EmotionToActionRule,
    ExplanatoryCompressRule,
    ExtensionRule,
    RegexRule,
    RuleBase,
    RuleRegistry,
    SubjectiveInternalizeRule,
    ThreatSubtextRule,
    create_extension_rules,
)

__all__ = [
    "SubtextEngine",
    "DialogueBlock",
    "RewriteResult",
    "RewriteRuleModel",
    "SubtextContext",
    "RuleBase",
    "RuleRegistry",
    "RegexRule",
    "ExplanatoryCompressRule",
    "EmotionToActionRule",
    "CausalToIronyRule",
    "SubjectiveInternalizeRule",
    "ThreatSubtextRule",
    "ComplianceSubvertRule",
    "AddressDistanceRule",
    "ExtensionRule",
    "create_extension_rules",
]
