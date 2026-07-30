"""
services/structure_validator.py - 物語構造テンプレート検証

既知の物語構造論（三幕/起承転結/ヒーローズジャーニー）と照合し、
必須ビートの欠落・クライマックス位置のずれ・ペーシング偏りを検出する。
公開知識のみを使用し、外部API・スクレイピングに依存しない。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

STRUCTURE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "three_act": {
        "name": "三幕構成",
        "required_beats": [
            {"key": "inciting_incident", "label": "発端（動機付けの事件）", "phase": 0.1},
            {"key": "rising_action", "label": "上昇行動", "phase": 0.4},
            {"key": "midpoint", "label": "中点（ターニングポイント）", "phase": 0.5},
            {"key": "climax", "label": "クライマックス", "phase": 0.8},
            {"key": "resolution", "label": "結末（解決）", "phase": 0.95},
        ],
        "climax_min_phase": 0.66,
    },
    "kishotenketsu": {
        "name": "起承転結",
        "required_beats": [
            {"key": "ki", "label": "起（導入）", "phase": 0.1},
            {"key": "sho", "label": "承（展開）", "phase": 0.4},
            {"key": "ten", "label": "転（転換）", "phase": 0.7},
            {"key": "ketsu", "label": "結（結末）", "phase": 0.95},
        ],
        "climax_min_phase": 0.5,
    },
    "hero_journey": {
        "name": "ヒーローズジャーニー",
        "required_beats": [
            {"key": "ordinary_world", "label": "日常の世界", "phase": 0.05},
            {"key": "call_to_adventure", "label": "冒険の召喚", "phase": 0.15},
            {"key": "ordeal", "label": "試練", "phase": 0.6},
            {"key": "climax", "label": "クライマックス（帰還）", "phase": 0.85},
        ],
        "climax_min_phase": 0.66,
    },
}


def load_structure(name: str) -> Dict[str, Any]:
    """構造テンプレートを取得する。未知の場合は三幕構成を既定とする。"""
    return STRUCTURE_DEFINITIONS.get(name, STRUCTURE_DEFINITIONS["three_act"])


def assign_phases(chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """各章を 0..1 のフェーズ（出現位置）に割り当てる。"""
    n = len(chapters)
    if n == 0:
        return []
    return [
        {**ch, "_phase": round(i / max(n - 1, 1), 3)}
        for i, ch in enumerate(chapters)
    ]


def check_required_beats(assigned: List[Dict[str, Any]], structure: Dict[str, Any]) -> List[Dict[str, Any]]:
    """各必須ビートが「そのフェーズ付近に章が存在するか」を判定する。"""
    if not assigned:
        return [
            {"key": b["key"], "label": b["label"], "present": False, "expected_phase": b["phase"]}
            for b in structure["required_beats"]
        ]
    tol = 0.35
    results = []
    for beat in structure["required_beats"]:
        present = any(abs(c["_phase"] - beat["phase"]) <= tol for c in assigned)
        results.append(
            {"key": beat["key"], "label": beat["label"], "present": present, "expected_phase": beat["phase"]}
        )
    return results


def check_climax_placement(assigned: List[Dict[str, Any]], structure: Dict[str, Any]) -> Dict[str, Any]:
    """後半1/3等にクライマックス相当の章（tension が最大の章）があるかを検証する。"""
    min_phase = structure.get("climax_min_phase", 0.66)
    if not assigned:
        return {"ok": False, "reason": "章がありません", "climax_phase": None}
    best = max(assigned, key=lambda c: c.get("tension", 0) or 0)
    phase = best["_phase"]
    return {
        "ok": phase >= min_phase,
        "reason": "" if phase >= min_phase else "クライマックス相当の山場が前半に偏っています",
        "climax_phase": phase,
    }


def check_pacing(assigned: List[Dict[str, Any]]) -> Dict[str, Any]:
    """前半詰め込み/後半スカスカ等の偏りを検出する。"""
    if len(assigned) < 3:
        return {"ok": True, "reason": "章数が少なく判定省略", "skew": 0.0}
    first_half = sum(1 for c in assigned if c["_phase"] < 0.5)
    ratio = first_half / len(assigned)
    skew = round(abs(ratio - 0.5), 3)
    return {
        "ok": skew <= 0.3,
        "reason": "" if skew <= 0.3 else "章の配置が片寄っています（前半/後半の偏り）",
        "skew": skew,
    }


def validate(chapters: List[Dict[str, Any]], structure_name: str = "three_act") -> Dict[str, Any]:
    """物語構造検証レポートを生成する。"""
    structure = load_structure(structure_name)
    assigned = assign_phases(chapters)
    beats = check_required_beats(assigned, structure)
    climax = check_climax_placement(assigned, structure)
    pacing = check_pacing(assigned)
    missing = [b for b in beats if not b["present"]]
    return {
        "structure": structure["name"],
        "structure_key": structure_name,
        "total_chapters": len(chapters),
        "missing_beats": missing,
        "climax": climax,
        "pacing": pacing,
        "is_healthy": (not missing) and climax["ok"] and pacing["ok"],
    }


def list_structures() -> List[Dict[str, Any]]:
    return [
        {"key": k, "name": v["name"], "beats": [b["label"] for b in v["required_beats"]]}
        for k, v in STRUCTURE_DEFINITIONS.items()
    ]
