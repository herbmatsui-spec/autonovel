"""src/services/ebook/epub_generator.py - EPUB 3 縦書き電子書籍生成ファサード (v5.2.0)"""

from __future__ import annotations

from src.services.exporters.epub_vertical_styler import COMMERCIAL_VERTICAL_CSS

class EpubGenerator:
    """縦書きEPUB 3生成およびCSSスタイル検証ファサード."""

    @staticmethod
    def get_vertical_css() -> str:
        """KDP / 楽天Kobo 準拠の縦書きCSSスタイルを返却する."""
        return COMMERCIAL_VERTICAL_CSS

    @staticmethod
    def is_vertical_writing_mode(css: str) -> bool:
        """CSSが縦書き（vertical-rl）をサポートしているかを判定する."""
        return "writing-mode: vertical-rl" in css


__all__ = ["EpubGenerator", "COMMERCIAL_VERTICAL_CSS"]
