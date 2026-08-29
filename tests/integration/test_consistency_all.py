"""tests/integration/test_consistency_all.py"""
from src.consistency.engine import ConsistencyEngine
from src.consistency.checkers import get_default_checkers
from src.consistency.checkers.base import CheckContext
from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs
from src.filesystem_memory.writer import write_file


def test_all_checkers_run(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(1, 1)
    ensure_workspace_dirs(base)

    # Prepare minimal data to trigger all checkers
    write_file(
        base / "STORY_SUMMARY.md",
        """# あらすじ
## 未回収要素
- 魔王の再臨
""",
    )
    write_file(
        base / "WORLD.md",
        """# 世界観
```json
{"prohibited": ["魔法"]}
```""",
    )
    write_file(
        base / "CHARACTERS.md",
        """## 主人公
- 名前: 太郎
- 性格: 臆病""",
    )
    write_file(
        base / "memory/chapters/chapter_01.md",
        "2023年01月01日 太郎は果敢に突撃し、魔法を使った。",
    )
    write_file(
        base / "memory/chapters/chapter_02.md",
        "2023年02月01日 同じ内容。太郎は果敢に突撃し、魔法を使った。",
    )

    engine = ConsistencyEngine(get_default_checkers())
    findings = engine.run(CheckContext(book_id=1, branch_id=1))

    # Should have findings from all 5 checkers
    categories = {f.category for f in findings}
    assert "foreshadowing" in categories
    assert "timeline" in categories  # dates are chronological, so 0 findings is OK
    assert "character" in categories
    assert "world" in categories
    assert "duplicate" in categories

    # At least 4 categories should have findings (timeline may be clean)
    assert len(categories) >= 4