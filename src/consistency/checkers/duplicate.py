"""consistency/checkers/duplicate.py - 重複チャプターチェッカー"""
import re
from typing import List, Set
from itertools import combinations

from src.consistency.findings import Finding
from src.consistency.checkers.base import Checker, CheckContext
from src.filesystem_memory.paths import get_workspace_path
from src.filesystem_memory.reader import list_chapter_summaries, read_file


def _ngrams(text: str, n: int = 5) -> Set[str]:
    # Normalize: remove whitespace/punctuation
    words = re.findall(r"\w+", text)
    return set(tuple(words[i : i + n]) for i in range(max(0, len(words) - n + 1)))


def _jaccard(a: Set, b: Set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


class DuplicateChecker(Checker):
    name = "duplicate"
    category = "duplicate"

    def check(self, context: CheckContext) -> List[Finding]:
        files = list_chapter_summaries(context.book_id, context.branch_id)
        texts = {}
        for f in files:
            ep = re.search(r"chapter_(\d+)", f.name)
            ep_num = int(ep.group(1)) if ep else 0
            texts[ep_num] = read_file(f)

        findings = []
        for (ea, ta), (eb, tb) in combinations(texts.items(), 2):
            sim = _jaccard(_ngrams(ta), _ngrams(tb))
            if sim > 0.3:
                findings.append(
                    self._make_finding(
                        "medium",
                        f"第 {ea} 章と第 {eb} 章の類似度が {sim:.0%} です。",
                        "内容の重複を確認・修正してください。",
                    )
                )
        if not findings:
            findings.append(self._make_finding("low", "No duplicate chapters detected", ""))
        return findings
