"""filesystem_memory/writer.py - Markdown 書込"""
import re
from pathlib import Path
from typing import Optional


def write_file(path: Path, content: str) -> None:
    """ファイルに内容を書き込む（上書き）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_with_frontmatter(path: Path, metadata: dict, content: str) -> None:
    """YAML frontmatter 付きで書き込む"""
    try:
        import yaml
        fm = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
    except ImportError:
        fm = ""
    write_file(path, f"---\n{fm}---\n{content}")


def update_section(path: Path, section_name: str, new_content: str) -> None:
    """指定セクション（## 見出し）の内容だけを置換する"""
    if not path.exists():
        write_file(path, f"## {section_name}\n{new_content}")
        return

    text = read_file_safe(path)
    pattern = re.compile(
        rf"(##\s*{re.escape(section_name)}\n)(.*?)(?=\n##\s|\Z)",
        re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(
            lambda m: f"{m.group(1)}{new_content}\n", text, count=1
        )
    else:
        updated = f"{text}\n\n## {section_name}\n{new_content}\n"
    write_file(path, updated)


def read_file_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
