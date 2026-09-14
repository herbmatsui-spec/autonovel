import os
from pathlib import Path
import pytest
from src.backend.database.core import WorkspaceManager

def test_workspace_manager_get_path():
    path_str = WorkspaceManager.get_path("test.db")
    assert "test.db" in path_str
    assert isinstance(path_str, str)

def test_workspace_manager_create_snapshot(tmp_path, monkeypatch):
    # テスト用ダミーDBファイル作成
    db_file = tmp_path / "autonovel.db"
    db_file.write_text("dummy database content")
    
    snapshot_path = WorkspaceManager.create_snapshot(str(db_file))
    assert snapshot_path != ""
    assert Path(snapshot_path).exists()
    assert ".bak_" in snapshot_path

def test_workspace_manager_create_snapshot_non_existent():
    # 存在しないファイルの場合は空文字列を返す
    snapshot_path = WorkspaceManager.create_snapshot("/path/to/non_existent_file.db")
    assert snapshot_path == ""

def test_workspace_manager_list_backups(tmp_path, monkeypatch):
    from src.backend.database import core
    monkeypatch.setattr(core, "BASE_DIR", tmp_path)
    
    f1 = tmp_path / "test.bak_100.db"
    f2 = tmp_path / "test.bak_200.db"
    f1.write_text("bak1")
    f2.write_text("bak2")
    
    backups = WorkspaceManager.list_backups()
    assert len(backups) == 2
