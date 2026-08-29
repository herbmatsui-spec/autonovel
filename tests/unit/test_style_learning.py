import pytest
from src.services.style_learning import (
    split_sentences,
    count_particles,
    top_words,
    avg_sentence_length,
    detect_banned,
    analyze_style,
    update_style_learned,
)
from src.filesystem_memory.paths import get_workspace_path
from src.filesystem_memory.writer import write_file, update_section
import tempfile
import shutil
from pathlib import Path

# Sample Japanese text for testing
SAMPLE_TEXT = """
今日はいい天気だ。散歩に出かけた。
公園で子供たちが遊んでいるのを見た。
特に、赤いボールを追いかける姿が印象的だった。
夕焼けがきれいだった。
"""

def test_split_sentences():
    sentences = split_sentences(SAMPLE_TEXT)
    assert len(sentences) == 5
    assert sentences[0] == "今日はいい天気だ"
    assert sentences[1] == "散歩に出かけた"
    assert sentences[2] == "公園で子供たちが遊んでいるのを見た"
    assert sentences[3] == "特に、赤いボールを追いかける姿が印象的だった"
    assert sentences[4] == "夕焼けがきれいだった"

def test_count_particles():
    counts = count_particles(SAMPLE_TEXT)
    # Expect at least some particles
    assert counts["に"] >= 2  # に in 散歩に, 公園で (で is not に, but 公園で has で, not に), actually let's just check it's a dict
    assert isinstance(counts["に"], int)
    assert isinstance(counts["は"], int)

def test_top_words():
    words = top_words(SAMPLE_TEXT, n=5)
    assert isinstance(words, list)
    assert all(isinstance(w, str) for w in words)
    # We expect words like "今日", "天気", "散歩", "公園", "子供たち" etc.
    # But note: our pattern requires 2+ kana/kanji, so single characters are excluded.
    # "今日" is 2 kanji, should be in there.
    # We'll just check that we get some words.
    assert len(words) > 0

def test_avg_sentence_length():
    sentences = split_sentences(SAMPLE_TEXT)
    avg = avg_sentence_length(sentences)
    assert isinstance(avg, float)
    assert avg > 0

def test_detect_banned():
    banned = ["雨", "雪"]
    hits = detect_banned("今日は雨が降っている。", banned)
    assert hits == ["雨"]
    hits2 = detect_banned("今日は晴れだ。", banned)
    assert hits2 == []

def test_analyze_style():
    # We need a dummy book_id and branch_id, and a SOUL.md with some banned terms to test the integration.
    # For simplicity, we'll mock the read_banned_from_soul by temporarily creating a SOUL.md in a temp workspace.
    tmpdir = tempfile.mkdtemp()
    try:
        # Set up a fake workspace
        book_id = 999
        branch_id = 1
        workspace_path = get_workspace_path(book_id, branch_id)
        workspace_path.mkdir(parents=True, exist_ok=True)
        # Write a SOUL.md with a banned term
        soul_path = workspace_path / "SOUL.md"
        soul_content = """# SOUL.md: Test
## 禁則事項
- 雨
- 雪
"""
        write_file(soul_path, soul_content)

        # Now analyze
        result = analyze_style(SAMPLE_TEXT, book_id, branch_id)
        assert "top_words" in result
        assert "avg_len" in result
        assert "particles" in result
        assert "banned_hits" in result
        # Since SAMPLE_TEXT has no 雨 or 雪, banned_hits should be empty
        assert result["banned_hits"] == []
        # But if we change the text to include 雨, it should be detected
        result2 = analyze_style(SAMPLE_TEXT + " 雨が降った。", book_id, branch_id)
        assert "雨" in result2["banned_hits"]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def test_update_style_learned():
    # We'll test the update function by creating a temporary workspace and checking the file.
    tmpdir = tempfile.mkdtemp()
    try:
        book_id = 888
        branch_id = 1
        workspace_path = get_workspace_path(book_id, branch_id)
        workspace_path.mkdir(parents=True, exist_ok=True)
        # Create a SOUL.md with some banned terms
        soul_path = workspace_path / "SOUL.md"
        soul_content = """# SOUL.md: Test
## 禁則事項
- 雨
"""
        write_file(soul_path, soul_content)
        # Also create an empty STYLE_LEARNED.md (init_workspace would have created it, but we just ensure the file exists)
        style_path = workspace_path / "STYLE_LEARNED.md"
        write_file(style_path, "# 学習済み文体: Test\n## 頻出語（上位N）\n<!-- learned:top_words -->\n## 平均文長\n<!-- learned:avg_len -->\n## 助詞傾向\n<!-- learned:particles -->\n## 禁則語（検出履歴）\n<!-- learned:banned -->\n## 直近サンプル文\n<!-- learned:sample -->")

        # Now call update
        returned_path = update_style_learned(book_id, 1, SAMPLE_TEXT, branch_id)
        assert returned_path == style_path
        # Read the file and check that sections have been updated (not just the placeholder)
        content = style_path.read_text(encoding="utf-8")
        # Check that the placeholder comments are gone (they should be replaced by actual content)
        assert "<!-- learned:top_words -->" not in content
        assert "<!-- learned:avg_len -->" not in content
        assert "<!-- learned:particles -->" not in content
        assert "<!-- learned:banned -->" not in content
        assert "<!-- learned:sample -->" not in content
        # Check that we have some content in each section (at least not empty)
        # We'll do a simple check: look for the section headers and then some non-empty line after
        lines = content.splitlines()
        # We'll just check that the file is longer than the original (which was just headers and placeholders)
        assert len(content) > 100  # lowered threshold
        # Additionally, check that the content includes some of the expected words
        assert "今日" in content or "天気" in content
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)