"""伏線言及・回収検出パーサー (v5.0 Relational Memory)

生成された本文テキスト中に伏線キーワードが含まれているかを検出する。
高速な文字列マッチングベースの簡易検出器。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ForeshadowingMention:
    """検出された伏線への言及"""
    foreshadowing_id: int
    title: str
    mention_count: int
    context_snippets: list[str] = field(default_factory=list)
    is_resolution_candidate: bool = False


# 回収を示唆するキーワード群
_RESOLUTION_KEYWORDS = [
    "ついに", "やはり", "やっと", "ようやく",
    "明らかになった", "判明した", "真相", "正体",
    "解き明かされ", "答えが", "理由は", "原因は",
    "回収", "伏線", "あの時の",
]


def detect_foreshadowing_mentions(
    text: str,
    foreshadowings: list[Any],
) -> list[ForeshadowingMention]:
    """本文中に登場した伏線のリストを検出する。

    Args:
        text: 生成された本文テキスト
        foreshadowings: ForeshadowingModel or dict のリスト
            各要素は id, title, description を持つこと

    Returns:
        検出された ForeshadowingMention のリスト
    """
    if not text or not foreshadowings:
        return []

    mentions: list[ForeshadowingMention] = []

    for f in foreshadowings:
        f_id = f.get("id") if isinstance(f, dict) else getattr(f, "id", None)
        title = f.get("title") if isinstance(f, dict) else getattr(f, "title", "")
        desc = f.get("description") if isinstance(f, dict) else getattr(f, "description", "")

        if not title:
            continue

        # タイトルの出現回数をカウント
        count = text.count(title)
        if count == 0:
            # description のキーフレーズでも検索（2単語以上の場合）
            if desc and len(desc) >= 4:
                # description の先頭20文字で部分検索
                key_phrase = desc[:20]
                count = text.count(key_phrase)

        if count > 0:
            # 周辺コンテキストを抽出（最大3箇所）
            snippets = _extract_snippets(text, title, max_snippets=3)

            # 回収候補かどうかの判定
            is_resolution = _check_resolution_context(text, title)

            mentions.append(ForeshadowingMention(
                foreshadowing_id=f_id,
                title=title,
                mention_count=count,
                context_snippets=snippets,
                is_resolution_candidate=is_resolution,
            ))

    return mentions


def _extract_snippets(text: str, keyword: str, max_snippets: int = 3, window: int = 40) -> list[str]:
    """キーワード周辺のスニペットを抽出"""
    snippets = []
    start = 0
    while len(snippets) < max_snippets:
        idx = text.find(keyword, start)
        if idx == -1:
            break
        begin = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        snippet = text[begin:end].replace("\n", " ").strip()
        snippets.append(f"...{snippet}...")
        start = idx + len(keyword)
    return snippets


def _check_resolution_context(text: str, title: str) -> bool:
    """伏線タイトル周辺に回収を示唆するキーワードがあるかチェック"""
    # タイトルの前後100文字を検索対象とする
    for match in re.finditer(re.escape(title), text):
        begin = max(0, match.start() - 100)
        end = min(len(text), match.end() + 100)
        context_window = text[begin:end]
        for kw in _RESOLUTION_KEYWORDS:
            if kw in context_window:
                return True
    return False
