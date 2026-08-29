"""tests/unit/test_duplicate_checker.py"""
from src.consistency.checkers.duplicate import DuplicateChecker
from src.consistency.checkers.base import CheckContext
from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs
from src.filesystem_memory.writer import write_file


def test_duplicate_checker_high_similarity(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(1, 1)
    ensure_workspace_dirs(base)
    # Two chapters with very similar text
    text = "太郎は森へ行った。そこで怪物と戦った。勝利して帰った。"
    write_file(base / "memory/chapters/chapter_01.md", text)
    write_file(base / "memory/chapters/chapter_02.md", text + " さらに続く。")

    checker = DuplicateChecker()
    findings = checker.check(CheckContext(book_id=1, branch_id=1))
    assert len(findings) == 1
    assert findings[0].category == "duplicate"
    assert "類似度" in findings[0].description


def test_duplicate_checker_low_similarity(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(2, 1)
    ensure_workspace_dirs(base)
    write_file(base / "memory/chapters/chapter_01.md", "太郎は森へ行った。")
    write_file(base / "memory/chapters/chapter_02.md", "花子は海へ行った。")

    checker = DuplicateChecker()
    findings = checker.check(CheckContext(book_id=2, branch_id=1))
    assert findings == []


def test_duplicate_checker_three_chapters(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(3, 1)
    ensure_workspace_dirs(base)
    base_text = "共通の文章が含まれている。" * 10
    write_file(base / "memory/chapters/chapter_01.md", base_text + " 章1")
    write_file(base / "memory/chapters/chapter_02.md", base_text + " 章2")
    write_file(base / "memory/chapters/chapter_03.md", "全く異なる内容です。")

    checker = DuplicateChecker()
    findings = checker.check(CheckContext(book_id=3, branch_id=1))
    # Should detect 01-02 as similar
    assert len(findings) == 1