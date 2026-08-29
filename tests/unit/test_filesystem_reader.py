"""tests/unit/test_filesystem_reader.py"""
from pathlib import Path

from src.filesystem_memory.reader import (
    read_file,
    read_with_frontmatter,
    list_chapter_summaries,
)
from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs


def test_read_file_normal(tmp_path):
    f = tmp_path / "test.md"
    f.write_text("# Hello\nWorld", encoding="utf-8")
    assert read_file(f) == "# Hello\nWorld"


def test_read_file_missing(tmp_path):
    f = tmp_path / "nope.md"
    try:
        read_file(f)
        assert False, "FileNotFoundError が発生するはず"
    except FileNotFoundError:
        pass


def test_read_with_frontmatter(tmp_path):
    f = tmp_path / "fm.md"
    f.write_text("---\ntitle: X\n---\n# Body\nText", encoding="utf-8")
    meta, body = read_with_frontmatter(f)
    assert meta.get("title") == "X"
    assert "Body" in body


def test_list_chapter_summaries(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    target = gwp(1, 1)
    ensure_workspace_dirs(target)
    (target / "memory" / "chapters" / "chapter_01.md").write_text("a")
    (target / "memory" / "chapters" / "chapter_02.md").write_text("b")
    files = list_chapter_summaries(1, 1)
    assert len(files) == 2
