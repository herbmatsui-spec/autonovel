"""
Unit tests for RuleBase and RuleRegistry (Step 3).
"""

import pytest
from src.narrative.subtext_engine.models import DialogueBlock, RewriteResult
from src.narrative.subtext_engine.rules import RuleBase, RuleRegistry


class DummyRule(RuleBase):
    def __init__(self, rule_id: str, priority: int = 100):
        super().__init__(rule_id=rule_id, priority=priority)

    def apply(self, block: DialogueBlock, context=None) -> RewriteResult:
        new_block = block.clone()
        new_block.lines.append(f"modified_by_{self.id}")
        return RewriteResult(success=True, modified=True, block=new_block, applied_rule_id=self.id)


def test_rule_registry_operations():
    registry = RuleRegistry()
    r1 = DummyRule("rule_b", priority=50)
    r2 = DummyRule("rule_a", priority=10)
    r3 = DummyRule("rule_c", priority=100)

    registry.register(r1)
    registry.register(r2)
    registry.register(r3)

    assert registry.get("rule_a") == r2
    assert registry.get("rule_nonexistent") is None

    ordered_rules = registry.list_rules()
    assert [r.id for r in ordered_rules] == ["rule_a", "rule_b", "rule_c"]

    # Test unregister
    removed = registry.unregister("rule_b")
    assert removed == r1
    assert len(registry.list_rules()) == 2

    registry.clear()
    assert len(registry.list_rules()) == 0
