import tempfile
import shutil
from pathlib import Path
from src.services.style_prompt import build_style_injection
from src.filesystem_memory.paths import get_workspace_path

def test_build_style_injection():
    # Create a temporary directory for workspace root
    tmpdir = tempfile.mkdtemp()
    try:
        # Monkey-patch WORKSPACE_ROOT to point to tmpdir
        import src.filesystem_memory.paths as paths_module
        original_workspace_root = paths_module.WORKSPACE_ROOT
        paths_module.WORKSPACE_ROOT = paths_module.Path(tmpdir)

        book_id = 123
        branch_id = 2
        workspace_path = get_workspace_path(book_id, branch_id)
        workspace_path.mkdir(parents=True, exist_ok=True)
        style_path = workspace_path / "STYLE_LEARNED.md"

        # Write a sample STYLE_LEARNED.md
        style_content = """# 学習済み文体: Test Book
## 頻出語（上位N）
吾輩, 猫, ですから
## 平均文長
25.6 文字
## 助詞傾向
は:10, が:5, を:8
## 禁則語（検出履歴）
雨, 雪
## 直近サンプル文
吾輩は猫である。名前はまだ無い。
"""
        style_path.write_text(style_content, encoding="utf-8")

        # Call the function
        injection = build_style_injection(book_id, branch_id)

# Assert that the injection string contains the expected parts
        assert "[学習済み文体]" in injection
        assert "頻出語: 吾輩, 猫, ですから" in injection
        assert "平均文長: 25.6 文字" in injection
        assert "助詞傾向: は:10, が:5, を:8" in injection
        assert "禁則語:" in injection
        assert "雨" in injection
        assert "雪" in injection
        assert "直近サンプル: 吾輩は猫である。名前はまだ無い。" in injection

        # Also test that if the file does not exist, we get empty string
        style_path.unlink()  # delete the file
        injection2 = build_style_injection(book_id, branch_id)
        assert injection2 == ""

        # Test that if the file exists but sections are empty, we get empty string
        style_path.write_text("# 学習済み文体: Test\n## 頻出語（上位N）\n## 平均文長\n## 助詞傾向\n## 禁則語（検出履歴）\n## 直近サンプル文\n", encoding="utf-8")
        injection3 = build_style_injection(book_id, branch_id)
        assert injection3 == ""

    finally:
        # Restore
        paths_module.WORKSPACE_ROOT = original_workspace_root
        shutil.rmtree(tmpdir, ignore_errors=True)