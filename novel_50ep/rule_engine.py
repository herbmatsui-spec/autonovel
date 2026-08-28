"""宣言的ルールエンジン基盤 (Phase 2 / ステップ 18〜23)"""

from __future__ import annotations
import glob
import os
from typing import Any, Dict, List, Optional
import yaml


def load_rules(dir_path: str) -> List[Dict[str, Any]]:
    """ルール定義 YAML ファイル群を読み込む (ステップ 18)"""
    rules: List[Dict[str, Any]] = []
    if not os.path.exists(dir_path):
        return rules
    pattern = os.path.join(dir_path, "*.yaml")
    for f in sorted(glob.glob(pattern)):
        try:
            with open(f, mode="r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
                if data and isinstance(data, dict):
                    rules.extend(data.get("rules", []))
        except Exception:
            continue
    return rules


def eval_rule(
    rule: Dict[str, Any],
    prev: Optional[Dict[str, Any]],
    cur: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """単一ルールの評価 (ステップ 19, 20, 21, 22, 35, 45)"""
    if cur is None:
        return []

    # ステップ 35: type 制限 (同種シーン間でのみルールを適用)
    if "type" in rule and rule["type"] is not None:
        if rule["type"] != cur.get("type") or (prev is not None and rule["type"] != prev.get("type")):
            return []

    op = rule.get("op")
    field = rule.get("field", "")
    msg = rule.get("msg", f"{field} の不整合")

    prev_val = prev.get(field) if prev is not None else None
    cur_val = cur.get(field)

    violations: List[Dict[str, Any]] = []

    # contains_forbidden は前シーン不要（単体チェック）
    if op == "contains_forbidden":
        forbidden = rule.get("forbidden", [])
        if isinstance(cur_val, str):
            for word in forbidden:
                if word in cur_val:
                    violations.append({
                        "field": field,
                        "msg": msg,
                        "rule": rule,
                        "found": word,
                    })
        return violations

    # 継続性チェック系は prev 必須
    if prev is None or prev_val is None or cur_val is None:
        return []

    if op == "equals":
        # ステップ 20: equals 評価
        if prev_val != cur_val:
            violations.append({
                "field": field,
                "msg": msg,
                "rule": rule,
                "prev": prev_val,
                "cur": cur_val,
            })

    elif op == "subset":
        # ステップ 21: subset 評価 (set(cur) <= set(prev))
        p_set = set(prev_val) if isinstance(prev_val, (list, set, tuple)) else set()
        c_set = set(cur_val) if isinstance(cur_val, (list, set, tuple)) else set()
        if not (c_set <= p_set):
            violations.append({
                "field": field,
                "msg": msg,
                "rule": rule,
                "prev": prev_val,
                "cur": cur_val,
            })

    elif op == "no_increase":
        # ステップ 22, 45: no_increase 評価 (cur <= prev, None 安全)
        if prev_val is None or cur_val is None:
            return []
        try:
            if float(cur_val) > float(prev_val):
                violations.append({
                    "field": field,
                    "msg": msg,
                    "rule": rule,
                    "prev": prev_val,
                    "cur": cur_val,
                })
        except (ValueError, TypeError):
            pass

    return violations


def check_scenes(
    prev: Optional[Dict[str, Any]],
    cur: Dict[str, Any],
    rules: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """全ルールを走査して違反リストを返す (ステップ 23)"""
    violations: List[Dict[str, Any]] = []
    
    for rule in rules:
        # contains_forbidden など単体チェック系は prev 不要
        op = rule.get("op")
        if op == "contains_forbidden":
            v = eval_rule(rule, prev, cur)
            if v:
                violations.extend(v)
        elif prev is not None:
            # 継続性チェック系は prev 必須
            v = eval_rule(rule, prev, cur)
            if v:
                violations.extend(v)
    return violations


def build_foreshadow_rules(expects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """伏線期待リストから動的ルールを生成 (ステップ 57)"""
    return [
        {
            "id": e.get("id"),
            "type": e.get("type"),
            "op": "equals",
            "field": e.get("field"),
            "msg": "伏線未回収",
        }
        for e in expects
    ]
