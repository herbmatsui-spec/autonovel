"""filesystem_memory/serializers.py - DTO -> Markdown 変換"""
from typing import Any, Dict, List


def serialize_soul(style: Dict[str, Any]) -> str:
    return (
        "# 執筆ペルソナ\n\n"
        "## 文体ガイド\n" + str(style.get("style_guide", "")) + "\n\n"
        "## トーンとリズム\n" + str(style.get("tone", "")) + "\n\n"
        "## 禁則事項\n" + str(style.get("prohibited", "")) + "\n"
    )


def serialize_world(bible: Dict[str, Any]) -> str:
    settings = bible.get("settings", {})
    import json

    return (
        "# 世界観\n\n"
        "## 概要\n" + str(bible.get("text", "")) + "\n\n"
        "## 特殊システム\n\n"
        "```json\n" + json.dumps(settings, ensure_ascii=False, indent=2) + "\n```\n"
    )


def serialize_characters(chars: List[Dict[str, Any]]) -> str:
    out = "# 登場人物\n\n"
    for c in chars:
        out += f"## {c.get('name', '名無し')}\n"
        for k, v in c.items():
            if k != "name":
                out += f"- {k}: {v}\n"
        out += "\n"
    return out


def serialize_outline(plots: List[Dict[str, Any]]) -> str:
    out = "# 全体構成\n\n"
    for p in plots:
        out += f"## 第 {p.get('ep_num')} 章: {p.get('title', '')}\n\n"
    return out
