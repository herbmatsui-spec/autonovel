from src.easy_mode.phase3.if_routes import (
    BranchCondition,
    ConditionOperator,
)


def test_branch_condition_equals():
    """等価条件の評価検証。"""
    cond = BranchCondition(
        variable="route",
        operator=ConditionOperator.EQUALS,
        value="heroine_a",
    )
    assert cond.evaluate({"route": "heroine_a"}) is True
    assert cond.evaluate({"route": "heroine_b"}) is False


def test_branch_condition_numeric_comparison():
    """数値比較条件の評価検証。"""
    cond_gt = BranchCondition(
        variable="player.affection",
        operator=ConditionOperator.GREATER_THAN,
        value=50,
    )
    assert cond_gt.evaluate({"player": {"affection": 60}}) is True
    assert cond_gt.evaluate({"player": {"affection": 40}}) is False
    assert cond_gt.evaluate({"player": {"affection": 50}}) is False


def test_branch_condition_contains():
    """含有・非含有条件の評価検証。"""
    cond_contains = BranchCondition(
        variable="inventory",
        operator=ConditionOperator.CONTAINS,
        value="legendary_sword",
    )
    assert cond_contains.evaluate({"inventory": ["potion", "legendary_sword"]}) is True
    assert cond_contains.evaluate({"inventory": ["potion"]}) is False
