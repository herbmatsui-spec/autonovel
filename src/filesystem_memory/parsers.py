"""filesystem_memory/parsers.py - Markdown -> DTO 変換（簡易実装）"""
import re
from typing import List, Dict, Any, Optional


def _split_sections(content: str) -> Dict[str, str]:
    """## 見出し でセクション分割"""
    sections: Dict[str, str] = {}
    current = None
    buf: List[str] = []
    for line in content.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def parse_soul(content: str) -> Dict[str, Any]:
    """SOUL.md -> dict (tone, style, prohibited)"""
    sections = _split_sections(content)
    return {
        "tone": sections.get("トーンとリズム", ""),
        "style_guide": sections.get("文体ガイド", ""),
        "prohibited": sections.get("禁則事項", ""),
    }


def parse_world(content: str) -> Dict[str, Any]:
    """WORLD.md -> dict (settings json if present)"""
    data: Dict[str, Any] = {"text": content}
    # Try to extract ```json block
    m = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if m:
        try:
            import json

            data["settings"] = json.loads(m.group(1))
        except Exception:
            data["settings"] = {}
    else:
        data["settings"] = {}
    return data


def parse_characters(content: str) -> List[Dict[str, Any]]:
    """CHARACTERS.md -> list of character dicts"""
    chars: List[Dict[str, Any]] = []
    # Split by '## ' headers that look like character names
    blocks = re.split(r"^##\s+", content, flags=re.MULTILINE)
    for blk in blocks[1:]:  # first part is before first ##
        lines = blk.splitlines()
        name = lines[0].strip() if lines else ""
        if not name:
            continue
        char = {"name": name}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                char[k.strip()] = v.strip()
        chars.append(char)
    return chars


def parse_outline(content: str) -> List[Dict[str, Any]]:
    """OUTLINE.md -> list of chapter dicts"""
    chapters: List[Dict[str, Any]] = []
    # Match '# 第 N 章: title' or '## 第 N 章: title'
    for m in re.finditer(r"^#+\s*第\s*(\d+)\s*章[:：]?\s*(.*)$", content, re.MULTILINE):
        ep_num = int(m.group(1))
        title = m.group(2).strip()
        chapters.append({"ep_num": ep_num, "title": title})
    return chapters
