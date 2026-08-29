"""filesystem_memory/reader.py - Markdown 読込"""
import re
from pathlib import Path
from typing import Tuple, List, Optional


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def read_file(path: Path) -> str:
    """ファイル内容を文字列で返す"""
    return path.read_text(encoding="utf-8")


def read_with_frontmatter(path: Path) -> Tuple[dict, str]:
    """YAML frontmatter + 本文を分離して返す"""
    try:
        import yaml
    except ImportError:
        yaml = None

    content = read_file(path)
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}, content

    fm_text, body = m.group(1), m.group(2)
    metadata = {}
    if yaml is not None:
        try:
            metadata = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            metadata = {}
    return metadata, body


def list_chapter_summaries(book_id: int, branch_id: int = 1) -> List[Path]:
    """memory/chapters 配下のチャプター要約ファイル一覧を返す"""
    from src.filesystem_memory.paths import get_workspace_path

    base = get_workspace_path(book_id, branch_id) / "memory" / "chapters"
    if not base.exists():
        return []
    return sorted(base.glob("chapter_*.md"))
