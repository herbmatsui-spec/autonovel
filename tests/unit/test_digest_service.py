"""ディジェクトサービスのユニットテスト。"""
from __future__ import annotations

from src.services.digest_service import CHAPTER_MAX_LENGTH, generate_suggestions, process_chapter


def test_process_chapter_normal_length():
    """Normal length chapter returns as-is."""
    result = process_chapter("短い章です")
    assert result == "短い章です"


def test_process_chapter_exact_max():
    """Exactly CHAPTER_MAX_LENGTH characters returns as-is."""
    result = process_chapter("あ" * CHAPTER_MAX_LENGTH)
    assert result == "あ" * CHAPTER_MAX_LENGTH


def test_process_chapter_over_max():
    """Over CHAPTER_MAX_LENGTH gets truncated with ..."""
    long_text = "あ" * (CHAPTER_MAX_LENGTH + 10)
    result = process_chapter(long_text)
    expected = "あ" * CHAPTER_MAX_LENGTH + "..."
    assert result == expected


def test_process_chapter_empty_string():
    """Empty string returns empty string."""
    result = process_chapter("")
    assert result == ""


def test_process_chapter_with_whitespace():
    """Whitespace-only chapter returns stripped with ..."""
    # len("   ") = 3 which is not > 1500, so returns as-is: "   "
    # but rstrip would give "" + "..."
    # Actually the function returns chapter as-is when len <= MAX
    result = process_chapter("   ")
    # Function returns input as-is when len <= CHAPTER_MAX_LENGTH
    assert result == "   "


async def test_generate_suggestions_empty():
    """Empty chapter returns default suggestions."""
    result = await generate_suggestions("")
    assert result == [
        "続行: (空章のため先頭から再開)",
        "調査が必要な未確認な要素を指摘",
    ]


async def test_generate_suggestions_with_chapter():
    """Non-empty chapter returns suggestions with prefix."""
    chapter = " test chapter text "
    result = await generate_suggestions(chapter)
    assert len(result) == 2
    assert result[0].startswith("続行: ")
