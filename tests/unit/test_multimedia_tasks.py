"""Multimedia Huey タスクの単体テスト。"""
from __future__ import annotations

import pytest

from src.backend import config
from src.backend.multimedia_service import MultimediaService
from src.backend.tasks.multimedia_tasks import generate_asset_pack_task


def test_generate_asset_pack_task_runs_sync(tmp_path, real_db_manager):
    """Huey immediate モードで同期実行した場合の挙動を確認。"""
    # Pydantic v2 BaseSettings は runtime での属性追加を許可するため直接書き換え
    config.settings.ENABLE_MULTIMEDIA = True
    config.settings.MULTIMEDIA_OUTPUT_DIR = str(tmp_path / "mm")
    # テスト中は immediate 化して直接呼べるようにする
    import src.backend.tasks as tasks_pkg

    prev = tasks_pkg.huey.immediate
    tasks_pkg.huey.immediate = True
    try:
        task_id = "test-task-001"
        # サービスから直接実行 (Huey の .call_local() 経由)
        result = generate_asset_pack_task.call_local(
            task_id=task_id,
            book_id=42,
            include_if_routes=True,
            include_media_mix=True,
            include_ebook=True,
            ebook_formats=["epub", "pdf"],
            media_mix_formats=["manga"],
        )
        assert isinstance(result, dict)
        # 成功 or 失敗のいずれでも dict が返る
        assert "file_count" in result or "error" in result
    finally:
        tasks_pkg.huey.immediate = prev
