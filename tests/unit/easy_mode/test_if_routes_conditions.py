import pytest
from src.easy_mode.phase3.if_routes import BranchCondition, ConditionOperator

def test_condition_operator_eval():
    cond = BranchCondition(
        variable="affection",
        operator=ConditionOperator.GREATER_EQUAL,
        value=80
    )
    assert cond.evaluate({"affection": 85}) is True
    assert cond.evaluate({"affection": 70}) is False