"""consistency/checkers/base.py - Checker 基底クラス"""
from abc import ABC, abstractmethod
from typing import List, Optional

from src.consistency.findings import Finding


class CheckContext:
    """チェック実行用コンテキスト（遅延ロード想定）"""

    def __init__(self, book_id: int, branch_id: int = 1, ep_num: Optional[int] = None):
        self.book_id = book_id
        self.branch_id = branch_id
        self.ep_num = ep_num


class Checker(ABC):
    name: str = "base"
    category: str = "generic"

    @abstractmethod
    def check(self, context: CheckContext) -> List[Finding]:
        ...

    def _make_finding(self, severity: str, description: str, suggestion: str = "") -> Finding:
        return Finding(
            category=self.category,
            severity=severity,
            description=description,
            suggestion=suggestion,
        )
