"""consistency/checkers/foreshadowing.py - 伏線未回収チェッカー"""
import re
from typing import List

from src.consistency.findings import Finding, Evidence
from src.consistency.checkers.base import Checker, CheckContext
from src.filesystem_memory.paths import get_workspace_path
from src.filesystem_memory.reader import read_file


class ForeshadowingChecker(Checker):
    name = "foreshadowing"
    category = "foreshadowing"

    def check(self, context: CheckContext) -> List[Finding]:
        base = get_workspace_path(context.book_id, context.branch_id)
        path = base / "STORY_SUMMARY.md"
        if not path.exists():
            return []
        content = read_file(path)
        # Look for "未回収要素" section
        m = re.search(r"##\s*未回収要素\s*(.*?)(\n##|\Z)", content, re.DOTALL)
        if not m:
            return []
        items = [ln.strip("- ").strip() for ln in m.group(1).splitlines() if ln.strip()]
        items = [i for i in items if i]
        findings = []
        for item in items:
            if "なし" in item or "（" in item and "）" in item and len(item) < 3:
                continue
            findings.append(
                self._make_finding(
                    "high",
                    f"未回収の伏線/謎: {item}",
                    "今後の章で回収するか、意図的な曖昧さとして却下してください。",
                )
            )
        return findings
