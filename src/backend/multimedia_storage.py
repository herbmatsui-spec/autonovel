"""Multimedia 成果物の出力ディレクトリ管理。

`MULTIMEDIA_OUTPUT_DIR` を冪等に作成し、絶対 Path を返す。
"""
from __future__ import annotations

from pathlib import Path

from src.backend.config import settings

__all__ = ["ensure_multimedia_dir", "get_multimedia_dir"]


def get_multimedia_dir() -> Path:
    """設定値から出力ディレクトリを Path で取得する。"""
    return Path(settings.MULTIMEDIA_OUTPUT_DIR).expanduser().resolve()


def ensure_multimedia_dir() -> Path:
    """出力ディレクトリを冪等に作成して返す。"""
    base = get_multimedia_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base
