"""consistency/engine.py - 整合性エンジン本体"""
from typing import List

from src.consistency.findings import Finding
from src.consistency.checkers.base import Checker, CheckContext


class ConsistencyEngine:
    def __init__(self, checkers: List[Checker]):
        self.checkers = checkers

    def run(self, context: CheckContext) -> List[Finding]:
        findings: List[Finding] = []
        for checker in self.checkers:
            try:
                results = checker.check(context)
                findings.extend(results)
            except Exception as e:
                # A failing checker shouldn't break the whole run
                import logging

                logging.getLogger(__name__).warning(
                    f"Checker {checker.name} failed: {e}"
                )
        return findings
