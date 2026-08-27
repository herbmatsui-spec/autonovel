"""Phase 2 テスト: ルールエンジンの評価テスト (ステップ 24)"""

import pytest
from novel_50ep.rule_engine import load_rules, eval_rule, check_scenes


def test_eval_rule_equals():
    rule = {"op": "equals", "field": "location", "msg": "場所不一致"}
    prev = {"location": "王都"}
    cur_match = {"location": "王都"}
    cur_mismatch = {"location": "迷宮"}

    assert eval_rule(rule, prev, cur_match) == []
    v = eval_rule(rule, prev, cur_mismatch)
    assert len(v) == 1
    assert v[0]["field"] == "location"
    assert v[0]["msg"] == "場所不一致"


def test_eval_rule_subset():
    rule = {"op": "subset", "field": "speakers", "msg": "未登場話者"}
    prev = {"speakers": ["凛", "セリア"]}
    cur_ok = {"speakers": ["凛"]}
    cur_ng = {"speakers": ["凛", "ガルド"]}

    assert eval_rule(rule, prev, cur_ok) == []
    v = eval_rule(rule, prev, cur_ng)
    assert len(v) == 1
    assert v[0]["field"] == "speakers"


def test_eval_rule_no_increase():
    rule = {"op": "no_increase", "field": "hp", "msg": "HP不正回復"}
    prev = {"hp": 50}
    cur_decrease = {"hp": 40}
    cur_same = {"hp": 50}
    cur_increase = {"hp": 60}

    assert eval_rule(rule, prev, cur_decrease) == []
    assert eval_rule(rule, prev, cur_same) == []
    v = eval_rule(rule, prev, cur_increase)
    assert len(v) == 1
    assert v[0]["field"] == "hp"
    assert v[0]["msg"] == "HP不正回復"


def test_check_scenes_multiple_rules():
    rules = [
        {"op": "equals", "field": "location", "msg": "場所不一致"},
        {"op": "no_increase", "field": "hp", "msg": "HP増加"},
    ]
    prev = {"location": "王都", "hp": 50}
    cur = {"location": "迷宮", "hp": 70}

    v = check_scenes(prev, cur, rules)
    assert len(v) == 2
