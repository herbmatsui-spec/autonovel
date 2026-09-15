from __future__ import annotations

import pytest
from src.services.exporters.base import escape_ruby_markup, process_ruby_markup


def test_ebook_ruby_markup_narou():
    """小説家になろう形式のルビ変換テスト"""
    src = "彼女は|林檎《りんご》|を食べた。"
    converted = process_ruby_markup(src, platform="narou")
    assert "|林檎《りんご》|" in converted


def test_ebook_ruby_markup_kakuyomu():
    """カクヨム形式のルビ変換テスト"""
    src = "彼女は|林檎《りんご》|を食べた。"
    converted = process_ruby_markup(src, platform="kakuyomu")
    assert "|林檎《りんご》|" in converted


def test_ebook_ruby_markup_markdown():
    """Markdown/HTML形式のルビ変換テスト"""
    src = "彼女は|林檎《りんご》|を食べた。"
    converted = process_ruby_markup(src, platform="markdown")
    assert "<ruby>林檎<rt>りんご</rt></ruby>" in converted


def test_ebook_ruby_markup_plain_text():
    """プレーンテキスト形式のルビ除去テスト"""
    src = "彼女は|林檎《りんご》|を食べた。"
    converted = process_ruby_markup(src, platform="txt")
    assert "林檎" in converted
    assert "《" not in converted


def test_ebook_escape_ruby_markup():
    """エスケープ処理のテスト（現行実装はそのまま保持）"""
    src = "パイプ記号 | と 《二重山括弧》"
    assert escape_ruby_markup(src) == src