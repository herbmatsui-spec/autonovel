"""tests/unit/test_filesystem_writer.py"""
from pathlib import Path

from src.filesystem_memory.writer import (
    write_file,
    write_with_frontmatter,
    update_section,
)


def test_write_file(tmp_path):
    f = tmp_path / "a.md"
    write_file(f, "hello")
    assert f.read_text(encoding="utf-8") == "hello"


def test_write_file_creates_parent(tmp_path):
    f = tmp_path / "sub" / "b.md"
    write_file(f, "x")
    assert f.exists()


def test_write_with_frontmatter(tmp_path):
    f = tmp_path / "fm.md"
    write_with_frontmatter(f, {"title": "T"}, "# Body")
    text = f.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "title: T" in text
    assert "Body" in text


def test_update_section_new(tmp_path):
    f = tmp_path / "s.md"
    update_section(f, "テスト", "内容")
    assert "## テスト" in f.read_text(encoding="utf-8")


def test_update_section_existing(tmp_path):
    f = tmp_path / "s.md"
    f.write_text("## A\nold\n## B\nkeep\n", encoding="utf-8")
    update_section(f, "A", "new")
    out = f.read_text(encoding="utf-8")
    assert "new" in out
    assert "keep" in out
    assert "old" not in out
