"""consistency/checkers/timeline.py - タイムライン矛盾チェッカー"""
import re
from typing import List

from src.consistency.findings import Finding
from src.consistency.checkers.base import Checker, CheckContext
from src.filesystem_memory.paths import get_workspace_path
from src.filesystem_memory.reader import list_chapter_summaries, read_file


class TimelineChecker(Checker):
    name = "timeline"
    category = "timeline"

    def check(self, context: CheckContext) -> List[Finding]:
        files = list_chapter_summaries(context.book_id, context.branch_id)
        dates = {}
        for f in files:
            text = read_file(f)
            # crude date extraction: YYYY年MM月DD日
            for m in re.finditer(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text):
                y, mo, d = map(int, m.groups())
                ep = re.search(r"chapter_(\d+)", f.name)
                ep_num = int(ep.group(1)) if ep else 0
                dates[ep_num] = (y, mo, d)
        # Check chronological order
        findings = []
        prev = None
        for ep_num in sorted(dates):
            cur = dates[ep_num]
            if prev and cur < prev:
                findings.append(
                    self._make_finding(
                        "medium",
                        f"第 {ep_num} 章の日付 ({cur}) が前章 ({prev}) より過去になっています。",
                        "タイムラインを見直してください。",
                    )
                )
            prev = cur
        return findings
