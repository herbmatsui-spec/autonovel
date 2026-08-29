"""consistency/filters.py - Finding フィルタ"""
from typing import List, Set

from src.consistency.findings import Finding


def filter_intentional(
    findings: List[Finding], dismissed_keys: Set[str]
) -> List[Finding]:
    """is_intentional または dismissed_keys に含まれるものを除外"""
    result = []
    for f in findings:
        if f.is_intentional:
            continue
        if f.key() in dismissed_keys:
            continue
        result.append(f)
    return result
