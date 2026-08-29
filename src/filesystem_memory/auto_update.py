"""filesystem_memory/auto_update.py - 章完了時の自動更新"""
import re
from pathlib import Path
from typing import Optional

from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs
from src.filesystem_memory.writer import write_file


def generate_chapter_summary(chapter_content: str, max_len: int = 300) -> str:
    """章本文から簡易要約を生成（LLM なし、先頭 N 文字 + 構造抽出）"""
    # Remove markdown headers
    lines = [
        ln for ln in chapter_content.splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    text = " ".join(lines)
    # First N chars as a naive summary
    summary = text[:max_len].strip()
    if len(text) > max_len:
        summary += "…"
    return summary or "（空の章）"


def update_chapter_memory(
    book_id: int, ep_num: int, summary: str, branch_id: int = 1
) -> Path:
    """memory/chapters/chapter_NN.md を生成・更新"""
    base = get_workspace_path(book_id, branch_id)
    ensure_workspace_dirs(base)
    filename = f"chapter_{ep_num:02d}.md"
    path = base / "memory" / "chapters" / filename
    content = f"# 第 {ep_num} 章 要約\n\n{summary}\n"
    write_file(path, content)
    return path


def update_story_summary(book_id: int, ep_num: int, summary: str, branch_id: int = 1) -> None:
    """STORY_SUMMARY.md の「現在の章まで」セクションを更新"""
    from src.filesystem_memory.writer import update_section

    path = get_workspace_path(book_id, branch_id) / "STORY_SUMMARY.md"
    update_section(path, "現在の章まで", f"- 第 {ep_num} 章: {summary}")
