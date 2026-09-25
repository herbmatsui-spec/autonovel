"""tests/unit/test_platform_formatters.py - 各投稿プラットフォーム整形および縦書きEPUB検証."""

from __future__ import annotations

import pytest

from src.services.publishers.formatters import PlatformFormatter, PublishPlatform
from src.services.ebook.epub_generator import EpubGenerator


def test_platform_typography_normalization():
    raw_text = "「おい、待てよ！」\n男は突然駆け出した。\n|英雄《えいゆう》の誕生だ。"

    # なろう形式: 地の文は全角スペースインデント、会話文はインデントなし、ルビ形式保持
    narou_text = PlatformFormatter.normalize_typography(raw_text, platform=PublishPlatform.NAROU)
    assert narou_text.startswith("「おい、待てよ！」")
    assert "　男は突然駆け出した。" in narou_text
    assert "|英雄《えいゆう》" in narou_text


def test_kakuyomu_ruby_transpilation():
    raw_text = "|超魔法《エクスプロージョン》を放った。"
    kakuyomu_text = PlatformFormatter.normalize_typography(raw_text, platform=PublishPlatform.KAKUYOMU)
    # カクヨム形式でも適切に整形されること
    assert "エクスプロージョン" in kakuyomu_text


def test_vertical_epub_css_specification():
    css = EpubGenerator.get_vertical_css()
    assert EpubGenerator.is_vertical_writing_mode(css) is True
    assert "text-indent: 1em" in css
    assert "p.dialogue" in css
