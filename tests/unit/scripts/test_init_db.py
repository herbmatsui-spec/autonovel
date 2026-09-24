"""Step 3 検証テスト: scripts/init_db.py の単体テスト。"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from init_db import _has_user_tables, run_migrations  # noqa: E402


def _create_db_with_table(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE sample_table (id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()


class TestHasUserTables:
    def test_missing_db_returns_false(self, tmp_path):
        assert _has_user_tables(tmp_path / "test.db") is False

    def test_empty_db_returns_false(self, tmp_path):
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        conn.close()
        assert _has_user_tables(db) is False

    def test_alembic_only_db_returns_false(self, tmp_path):
        """alembic_version のみの DB は「ユーザーテーブルなし」とみなす。"""
        db = tmp_path / "test.db"
        conn = sqlite3.connect(str(db))
        try:
            conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32))")
            conn.commit()
        finally:
            conn.close()
        assert _has_user_tables(db) is False

    def test_db_with_table_returns_true(self, tmp_path):
        db = tmp_path / "test.db"
        _create_db_with_table(db)
        assert _has_user_tables(db) is True

    def test_corrupted_db_returns_true_for_protection(self, tmp_path):
        """破損 DB は保護のため「テーブルあり」とみなす。"""
        db = tmp_path / "test.db"
        db.write_bytes(b"this is not a sqlite database" * 10)
        assert _has_user_tables(db) is True


class TestRunMigrations:
    def test_skips_existing_db(self, tmp_path, capsys):
        """既存 DB がある場合はマイグレーションをスキップする。"""
        db = tmp_path / "test.db"
        _create_db_with_table(db)
        fake_ini = tmp_path / "alembic.ini"
        fake_ini.write_text("[alembic]\n")
        with patch("init_db.ALEMBIC_INI", fake_ini):
            assert run_migrations(db) is True
        output = capsys.readouterr().out
        assert "Skipping migration" in output

    def test_runs_migration_on_empty_db(self, tmp_path, capsys):
        """空の DB では alembic を呼び出す（失敗しても False を返す）。"""
        db = tmp_path / "test.db"
        fake_ini = tmp_path / "alembic.ini"
        fake_ini.write_text("[alembic]\n")
        with (
            patch("init_db.ALEMBIC_INI", fake_ini),
            patch("init_db.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            assert run_migrations(db) is True
        output = capsys.readouterr().out
        assert "alembic upgrade head" in output

    def test_returns_false_on_migration_failure(self, tmp_path):
        """alembic 失敗時は False を返す。"""
        db = tmp_path / "test.db"
        fake_ini = tmp_path / "alembic.ini"
        fake_ini.write_text("[alembic]\n")
        with (
            patch("init_db.ALEMBIC_INI", fake_ini),
            patch("init_db.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = "error"
            mock_run.return_value.stderr = "boom"
            assert run_migrations(db) is False

    def test_returns_false_without_alembic_ini(self, tmp_path):
        db = tmp_path / "test.db"
        with patch("init_db.ALEMBIC_INI", tmp_path / "missing.ini"):
            assert run_migrations(db) is False

    def test_force_overrides_skip(self, tmp_path, capsys):
        """--force 指定時は既存 DB でもマイグレーションを実行する。"""
        db = tmp_path / "test.db"
        _create_db_with_table(db)
        fake_ini = tmp_path / "alembic.ini"
        fake_ini.write_text("[alembic]\n")
        with (
            patch("init_db.ALEMBIC_INI", fake_ini),
            patch("init_db.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            assert run_migrations(db, force=True) is True
        output = capsys.readouterr().out
        assert "Skipping migration" not in output
