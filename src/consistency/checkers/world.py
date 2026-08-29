"""consistency/checkers/world.py - 世界観矛盾チェッカー"""
import re
from typing import List

from src.consistency.findings import Finding
from src.consistency.checkers.base import Checker, CheckContext
from src.filesystem_memory.paths import get_workspace_path
from src.filesystem_memory.reader import read_file, list_chapter_summaries
from src.filesystem_memory.parsers import parse_world


class WorldChecker(Checker):
    name = "world"
    category = "world"

    def check(self, context: CheckContext) -> List[Finding]:
        base = get_workspace_path(context.book_id, context.branch_id)
        world_path = base / "WORLD.md"
        if not world_path.exists():
            return []
        world = parse_world(read_file(world_path))
        settings = world.get("settings", {})
        # prohibited terms could be defined in settings["prohibited"]
        prohibited = settings.get("prohibited", []) if isinstance(settings, dict) else []
        if isinstance(prohibited, str):
            prohibited = [prohibited]
        findings = []
        for f in list_chapter_summaries(context.book_id, context.branch_id):
            text = read_file(f)
            for term in prohibited:
                if term and term in text:
                    findings.append(
                        self._make_finding(
                            "high",
                            f"世界観設定で禁止されている用語「{term}」が章要約に出現しています。",
                            "用語を修正するか、設定を更新してください。",
                        )
                    )
        return findings
