"""Unit tests for platform novel formatter and ruby transpiler (Steps 56, 57, 58)."""

import io
import zipfile
import pytest

from src.services.formatters.ruby_transpiler import PublishPlatform, RubyTranspiler
from src.services.formatters.platform_formatter import PlatformFormatter


def test_ruby_transpiler_narou():
    """Test ruby and bouten transpilation for Shousetsuka ni Narou."""
    text = "彼は｜魔法《マジック》を使った。《《必殺技》》だ！"
    result = RubyTranspiler.transpile_all(text, PublishPlatform.NAROU)
    assert "|魔法《マジック》" in result
    assert "|必《・》|殺《・》|技《・》" in result


def test_ruby_transpiler_kakuyomu():
    """Test ruby and bouten transpilation for Kakuyomu."""
    text = "彼女は｜世界《せかい》を守る。《《英雄》》である。"
    result = RubyTranspiler.transpile_all(text, PublishPlatform.KAKUYOMU)
    assert "|世界《せかい》" in result
    # Kakuyomu retains native bouten 《《...》》
    assert "《《英雄》》" in result


def test_ruby_transpiler_alphapolis():
    """Test ruby and bouten transpilation for Alphapolis."""
    text = "我が｜剣《つるぎ》を受けよ。《《覚悟》》！"
    result = RubyTranspiler.transpile_all(text, PublishPlatform.ALPHAPOLIS)
    assert "#剣(つるぎ)#" in result
    assert "#覚(・)##悟(・)#" in result


def test_ruby_transpiler_aozora():
    """Test ruby and bouten transpilation for Aozora Bunko."""
    text = "これは｜本《ほん》である。《《重要》》な事項。"
    result = RubyTranspiler.transpile_all(text, PublishPlatform.AOZORA)
    assert "｜本《ほん》" in result
    assert "［＃傍点］重要［＃傍点終わり］" in result


def test_typography_normalization():
    """Test indentation and typography normalization (Step 57)."""
    text = (
        "朝が来た。\n"
        "「おはよう」\n"
        "　すでに全角スペースがある行。\n"
        "\n\n\n\n"  # 4 blank lines
        "謎の声が響く……\n"
        "沈黙が流れた…\n"  # odd ellipsis (1) -> should become 2
    )

    result = PlatformFormatter.normalize_typography(text, PublishPlatform.NAROU)
    lines = result.split("\n")

    # Narrative lines should start with full-width space
    assert lines[0] == "　朝が来た。"
    # Dialogue line should not have full-width space
    assert lines[1] == "「おはよう」"
    # Existing indent preserved as single full-width space
    assert lines[2] == "　すでに全角スペースがある行。"

    # Ellipsis normalization: odd count becomes even
    assert "……" in result
    assert "沈黙が流れた……" in result

    # Consecutive blank lines should be capped
    assert "\n\n\n\n" not in result


def test_validation_limits():
    """Test title and synopsis length validations (Step 58)."""
    short_title = "短いタイトル"
    long_title = "あ" * 105
    short_synopsis = "あらすじです。"
    long_synopsis_narou = "あ" * 1500
    long_synopsis_kakuyomu = "あ" * 12000

    # Narou checks
    warnings_narou = PlatformFormatter.validate_limits(long_title, long_synopsis_narou, PublishPlatform.NAROU)
    assert len(warnings_narou) == 2
    assert "タイトル上限" in warnings_narou[0]
    assert "あらすじ" in warnings_narou[1]

    # Kakuyomu checks
    warnings_kakuyomu = PlatformFormatter.validate_limits(short_title, long_synopsis_kakuyomu, PublishPlatform.KAKUYOMU)
    assert len(warnings_kakuyomu) == 1
    assert "カクヨムのあらすじ上限" in warnings_kakuyomu[0]

    # Valid inputs
    warnings_ok = PlatformFormatter.validate_limits(short_title, short_synopsis, PublishPlatform.KAKUYOMU)
    assert len(warnings_ok) == 0


def test_format_episode_with_author_notes():
    """Test formatting with foreword and afterword (Step 54)."""
    formatted = PlatformFormatter.format_episode_with_author_notes(
        title="第1話 はじまり",
        content="冒頭の文。「こんにちは」",
        platform=PublishPlatform.KAKUYOMU,
        foreword="作者よりご挨拶",
        afterword="次回もお楽しみに！",
    )

    assert "【前書き】" in formatted["full_text"]
    assert "作者よりご挨拶" in formatted["full_text"]
    assert "【後書き】" in formatted["full_text"]
    assert "次回もお楽しみに！" in formatted["full_text"]
    assert "　冒頭の文。" in formatted["content"]


def test_package_for_platform_zip():
    """Test generating zip archive for publishing platform (Step 55)."""
    episodes = [
        {"title": "第一話", "content": "本文その1。「行くぞ」"},
        {"title": "第二話", "content": "本文その2。「了解」", "afterword": "またね"},
    ]

    zip_bytes = PlatformFormatter.package_for_platform(
        title="テスト作品",
        synopsis="テストのあらすじです。",
        episodes=episodes,
        platform=PublishPlatform.NAROU,
    )

    assert len(zip_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "00_作品情報・あらすじ.txt" in namelist
        assert "本文/001_第一話.txt" in namelist
        assert "本文/002_第二話.txt" in namelist

        ep1_text = zf.read("本文/001_第一話.txt").decode("utf-8")
        assert "　本文その1。" in ep1_text
        assert "「行くぞ」" in ep1_text
