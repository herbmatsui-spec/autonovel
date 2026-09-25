"""SQLite 自動マイグレーションスクリプト (Step 3).

初回起動時に Alembic マイグレーションを安全かつ確実に実行する。
テーブルが存在しない場合のみ `alembic upgrade head` を実行し、
既存 DB への破壊的干渉を防止する。

実行:
    python scripts/init_db.py [--force]

終了コード:
    0 : マイグレーション実行済み、または既存 DB が正常
    1 : マイグレーション失敗
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "autonovel.db"
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def _has_user_tables(db_path: Path) -> bool:
    """SQLite DB にユーザーテーブルが 1 つでも存在するか判定する。

    alembic_version テーブルはマイグレーション管理用メタデータなので
    「ユーザーテーブル」とはみなさない。
    """
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.execute(
                "SELECT count(*) FROM sqlite_master "
                "WHERE type='table' AND name != 'alembic_version'"
            )
            (count,) = cursor.fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        # DB が破損している場合は存在するとみなして保護（上書き防止）
        return True
    return count > 0


def run_migrations(db_path: Path = DEFAULT_DB_PATH, force: bool = False) -> bool:
    """Alembic マイグレーションを実行する。

    Args:
        db_path: SQLite DB ファイルのパス。
        force: True の場合、既存 DB があっても `alembic upgrade head` を実行する。

    Returns:
        マイグレーションが正常に完了した（または不要だった）場合 True。
    """
    if not ALEMBIC_INI.exists():
        print(f"[init_db] alembic.ini not found: {ALEMBIC_INI}")
        return False

    if _has_user_tables(db_path) and not force:
        print(f"[init_db] Existing database detected: {db_path}")
        print("[init_db] Skipping migration to avoid destructive interference.")
        print("[init_db] Use --force to run 'alembic upgrade head' anyway.")
        return True

    print(f"[init_db] Running 'alembic upgrade head' (db: {db_path}) ...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f"[init_db] Failed to launch alembic: {exc}")
        return False

    if result.returncode != 0:
        print("[init_db] Migration FAILED.")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False

    print("[init_db] Migration completed successfully.")
    return True


def main(argv: list[str] | None = None) -> int:
    """エントリポイント。終了コードを返す。"""
    parser = argparse.ArgumentParser(description="AutoNovel SQLite DB initializer")
    parser.add_argument(
        "--force",
        action="store_true",
        help="run alembic upgrade head even if tables already exist",
    )
    args = parser.parse_args(argv)
    return 0 if run_migrations(force=args.force) else 1


if __name__ == "__main__":
    sys.exit(main())
