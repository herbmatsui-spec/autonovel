"""filesystem_memory/paths.py - ワークスペースファイルパス定義"""
from pathlib import Path

WORKSPACE_ROOT = Path("./workspaces")

WORKSPACE_FILES = [
    "SOUL.md",
    "WORLD.md",
    "CHARACTERS.md",
    "OUTLINE.md",
    "STORY_SUMMARY.md",
    "MEMORY.md",
]


def get_workspace_path(book_id: int, branch_id: int = 1) -> Path:
    """book_id / branch_id からワークスペースディレクトリを取得"""
    return WORKSPACE_ROOT / f"book_{book_id}" / f"branch_{branch_id}"


def ensure_workspace_dirs(path: Path) -> None:
    """必要な全ディレクトリを作成（冪等）"""
    for sub in ["", "memory/chapters"]:
        (path / sub).mkdir(parents=True, exist_ok=True)
