#!/usr/bin/env python
"""
Schema drift check script for CI/CD.

Usage:
    python scripts/check_schema_drift.py          # Check drift, exit with code
    python scripts/check_schema_drift.py --fix    # Run migrations to fix drift
"""
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backend.database.schema_check import check_schema_drift, assert_no_schema_drift


def main():
    parser = argparse.ArgumentParser(description="Check for database schema drift")
    parser.add_argument(
        "--fix", action="store_true", help="Run alembic migrations to fix drift"
    )
    parser.add_argument(
        "--url", type=str, help="Database URL (overrides DATABASE_URL env var)"
    )
    args = parser.parse_args()

    os.environ.setdefault("KAKU_ENV", "test")

    print("Checking schema drift...")
    drift_info = check_schema_drift()

    if drift_info["has_drift"]:
        print("❌ Schema drift detected!")
        if drift_info["migration_mismatch"]:
            print(
                f"  Alembic revision mismatch: head={drift_info['alembic_head']}, "
                f"db={drift_info['db_revision']}"
            )
        if drift_info["missing_tables"]:
            print(f"  Missing tables: {drift_info['missing_tables']}")
        if drift_info["extra_tables"]:
            print(f"  Extra tables: {drift_info['extra_tables']}")

        if args.fix:
            print("\nAttempting to fix by running alembic migrations...")
            from alembic import command
            from alembic.config import Config
            from config import BASE_DIR, DATABASE_URL

            sync_url = args.url or DATABASE_URL
            if "sqlite+aiosqlite" in sync_url:
                sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
            elif "postgresql+asyncpg" in sync_url:
                sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

            ini_path = BASE_DIR / "alembic.ini"
            alembic_cfg = Config(str(ini_path))
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

            try:
                command.upgrade(alembic_cfg, "head")
                print("✅ Migrations applied successfully")
                sys.exit(0)
            except Exception as e:
                print(f"❌ Migration failed: {e}")
                sys.exit(1)
        else:
            print("\nRun with --fix to apply pending migrations")
            sys.exit(1)
    else:
        print("✅ No schema drift detected")
        sys.exit(0)


if __name__ == "__main__":
    main()