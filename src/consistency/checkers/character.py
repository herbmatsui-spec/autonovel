"""consistency/checkers/character.py - キャラ設定齟齬チェッカー"""
import re
from typing import List

from src.consistency.findings import Finding
from src.consistency.checkers.base import Checker, CheckContext
from src.filesystem_memory.paths import get_workspace_path
from src.filesystem_memory.reader import read_file, list_chapter_summaries
from src.filesystem_memory.parsers import parse_characters


class CharacterChecker(Checker):
    name = "character"
    category = "character"

    # Simple trait vs action contradiction pairs
    CONTRADICTIONS = [
        ("臆病", ["突撃", "果敢", "勇敢"]),
        ("無口", ["饒舌", "長談義"]),
        ("冷酷", ["優しく", "慈愛"]),
    ]

    def check(self, context: CheckContext) -> List[Finding]:
        base = get_workspace_path(context.book_id, context.branch_id)
        char_path = base / "CHARACTERS.md"
        if not char_path.exists():
            return []
        chars = parse_characters(read_file(char_path))
        findings = []
        for ch in chars:
            trait = ch.get("性格", "")
            name = ch.get("name", "")
            if not name:
                continue
            # Collect chapter summaries
            for f in list_chapter_summaries(context.book_id, context.branch_id):
                text = read_file(f)
                for trait_kw, action_kws in self.CONTRADICTIONS:
                    if trait_kw in trait:
                        for act in action_kws:
                            if act in text:
                                findings.append(
                                    self._make_finding(
                                        "medium",
                                        f"キャラ「{name}」は「{trait_kw}」と設定されていますが、"
                                        f"章要約に「{act}」的な行動が見られます。",
                                        "設定と行動の整合性を確認してください。",
                                    )
                                )
                                break
        return findings
