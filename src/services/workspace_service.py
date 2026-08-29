"""services/workspace_service.py - ワークスペース初期化・管理"""
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.filesystem_memory.paths import (
    get_workspace_path,
    ensure_workspace_dirs,
    WORKSPACE_FILES,
)
from src.filesystem_memory.writer import write_file

_TEMPLATE_DIR = (
    Path(__file__).resolve().parents[1]
    / "filesystem_memory"
    / "templates"
)

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Template filename -> context extractor
_TEMPLATE_FILES = {
    "SOUL.md": "SOUL.md.j2",
    "WORLD.md": "WORLD.md.j2",
    "CHARACTERS.md": "CHARACTERS.md.j2",
    "OUTLINE.md": "OUTLINE.md.j2",
    "STORY_SUMMARY.md": "STORY_SUMMARY.md.j2",
    "MEMORY.md": "MEMORY.md.j2",
}


def init_workspace(book_id: int, book: dict, branch_id: int = 1) -> List[Path]:
    """既存 book データからテンプレートを render し、6 ファイルを生成"""
    base = get_workspace_path(book_id, branch_id)
    ensure_workspace_dirs(base)

    generated = []
    for filename, template_name in _TEMPLATE_FILES.items():
        template = _env.get_template(template_name)
        rendered = template.render(book=book)
        target = base / filename
        write_file(target, rendered)
        generated.append(target)
    return generated
