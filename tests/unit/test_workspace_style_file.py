import os
import tempfile
import shutil
from src.services.workspace_service import init_workspace

def test_init_workspace_creates_style_learned_file():
    # Create a temporary directory for workspace root
    tmpdir = tempfile.mkdtemp()
    try:
        # Monkey-patch WORKSPACE_ROOT to point to tmpdir
        import src.filesystem_memory.paths as paths_module
        original_workspace_root = paths_module.WORKSPACE_ROOT
        paths_module.WORKSPACE_ROOT = paths_module.Path(tmpdir)

        # Dummy book data
        book = {"title": "Test Book", "genre": "fantasy"}

        # Call init_workspace
        generated = init_workspace(book_id=1, book=book, branch_id=1)

        # Determine the expected path
        expected_path = paths_module.get_workspace_path(1, 1) / "STYLE_LEARNED.md"
        # Check that the file exists
        assert expected_path.exists(), f"Expected file not found: {expected_path}"
        # Optionally, check that it's in the generated list (it should be)
        assert expected_path in generated, "STYLE_LEARNED.md not returned by init_workspace"

        # Read the file and check for section headings
        content = expected_path.read_text(encoding="utf-8")
        assert "# 学習済み文体: Test Book" in content
        assert "## 頻出語（上位N）" in content
        assert "## 平均文長" in content
        assert "## 助詞傾向" in content
        assert "## 禁則語（検出履歴）" in content
        assert "## 直近サンプル文" in content

    finally:
        # Restore original WORKSPACE_ROOT
        paths_module.WORKSPACE_ROOT = original_workspace_root
        # Clean up temp directory
        shutil.rmtree(tmpdir, ignore_errors=True)