"""
services/exporters/base.py - 出版フォーマット自動整形エクスポーター基底

各プラットフォーム（なろう/カクヨム/Nocturne）の投稿用テキスト整形を提供する。
自動投稿ではなく、人間がコピペ・貼り付けする用の整形済みテキストを出力する。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseExporter(ABC):
    """エクスポータの基底クラス。"""

    platform: str = "base"
    description: str = ""

    @abstractmethod
    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        """小説全体をプラットフォーム用テキストに整形して返す。"""

    def _header(self, novel: Dict[str, Any]) -> str:
        return f"# {novel.get('title', '無題')}\n\n{novel.get('synopsis', '')}\n"

    def _format_chapter(self, ch: Dict[str, Any]) -> str:
        title = ch.get("title") or f"第{ch.get('ep_num')}話"
        body = ch.get("content") or ""
        return f"## {title}\n\n{body}\n"


class NarouExporter(BaseExporter):
    platform = "narou"
    description = "小説家になろう（改行・ルビ・話区切りを標準整形）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        out = [self._header(novel)]
        for ch in chapters:
            out.append(self._format_chapter(ch))
            out.append("\n" + "=" * 20 + "\n")
        return "\n".join(out)


class KakuyomuExporter(BaseExporter):
    platform = "kakuyomu"
    description = "カクヨム（Markdown系・R18タグ付与）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        out = [f"# {novel.get('title', '無題')}", "", novel.get("synopsis", ""), ""]
        for ch in chapters:
            out.append(self._format_chapter(ch))
        if novel.get("is_adult"):
            out.append("\n[カクヨムR18タグ: 成人向け]\n")
        return "\n".join(out)


class NocturneExporter(BaseExporter):
    platform = "nocturn"
    description = "Nocturn Novel（官能タグ・年齢確認文言）"

    def export(self, novel: Dict[str, Any], chapters: List[Dict[str, Any]]) -> str:
        out = [f"# {novel.get('title', '無題')}", "", "[R18] 成年向けコンテンツを含みます。", ""]
        for ch in chapters:
            out.append(self._format_chapter(ch))
        out.append("\n[年齢確認: 18歳以上であることを確認しました]\n")
        return "\n".join(out)


_EXPORTERS = {
    NarouExporter.platform: NarouExporter,
    KakuyomuExporter.platform: KakuyomuExporter,
    NocturneExporter.platform: NocturneExporter,
}


def get_exporter(platform: str) -> BaseExporter:
    """プラットフォーム名からエクスポータを取得する。未知の場合はなろうを既定とする。"""
    cls = _EXPORTERS.get(platform, NarouExporter)
    return cls()


def list_platforms() -> List[Dict[str, str]]:
    """対応プラットフォーム一覧を返す。"""
    return [{"platform": e.platform, "description": e.description} for e in _EXPORTERS.values()]


def sanitize_for_platform(text: str) -> str:
    """プラットフォーム共通の軽いサニタイズ（制御文字除去）。"""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text or "")
