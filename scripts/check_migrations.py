#!/usr/bin/env python3
"""Alembic マイグレーション双方向（upgrade -> downgrade -> upgrade）自動検証スクリプト。"""
import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str], env: dict[str, str] | None = None) -> bool:
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}:")
        print(result.stderr)
        return False
    print(result.stdout)
    return True


def main() -> int:
    test_db = Path("test_migration.db")
    if test_db.exists():
        test_db.unlink()

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db.resolve()}"

    print("Step 1: Upgrading to head...")
    if not run_command(["alembic", "upgrade", "head"], env=env):
        return 1

    print("Step 2: Downgrading 1 revision...")
    if not run_command(["alembic", "downgrade", "-1"], env=env):
        return 1

    print("Step 3: Re-upgrading to head...")
    if not run_command(["alembic", "upgrade", "head"], env=env):
        return 1

    if test_db.exists():
        test_db.unlink()

    print("SUCCESS: Migration roundtrip verified successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
