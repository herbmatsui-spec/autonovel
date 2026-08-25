"""
Schema drift detection utility.

Compares alembic migration state with ORM model definitions to detect
schema drift in production environments.
"""
import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from config import BASE_DIR, DATABASE_URL
from src.backend.database.models import Base

logger = logging.getLogger(__name__)


def get_alembic_head_revision() -> Optional[str]:
    """Get the current alembic head revision from migrations."""
    ini_path = BASE_DIR / "alembic.ini"
    if not ini_path.exists():
        logger.warning("alembic.ini not found at %s", ini_path)
        return None

    sync_url = DATABASE_URL
    if "sqlite+aiosqlite" in sync_url:
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
    elif "postgresql+asyncpg" in sync_url:
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

    try:
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_heads()
        if heads:
            # Return first head (or could join them)
            return heads[0]
        return None
    except Exception as e:
        logger.error("Failed to get alembic head revision: %s", e)
        return None


def get_database_current_revision(sync_url: str) -> Optional[str]:
    """Get the current alembic revision stored in the database."""
    try:
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            # Check if alembic_version table exists
            result = conn.execute(text("""
                SELECT version_num FROM alembic_version LIMIT 1
            """))
            row = result.fetchone()
            if row:
                return row[0]
            return None
    except Exception as e:
        logger.debug("Could not read alembic_version table: %s", e)
        return None


def get_model_table_names() -> set:
    """Get table names defined in SQLAlchemy models."""
    return set(Base.metadata.tables.keys())


def get_database_table_names(sync_url: str) -> set:
    """Get table names currently in the database."""
    try:
        engine = create_engine(sync_url)
        inspector = inspect(engine)
        return set(inspector.get_table_names())
    except Exception as e:
        logger.error("Failed to inspect database tables: %s", e)
        return set()


def check_schema_drift(sync_url: Optional[str] = None) -> dict:
    """
    Check for schema drift between alembic migrations and ORM models.

    Returns a dict with drift information:
    - 'has_drift': bool
    - 'alembic_head': str or None
    - 'db_revision': str or None
    - 'missing_tables': list of tables in models but not in DB
    - 'extra_tables': list of tables in DB but not in models
    - 'migration_mismatch': bool (alembic head != db revision)
    """
    if sync_url is None:
        sync_url = DATABASE_URL
        if "sqlite+aiosqlite" in sync_url:
            sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
        elif "postgresql+asyncpg" in sync_url:
            sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

    result = {
        "has_drift": False,
        "alembic_head": None,
        "db_revision": None,
        "missing_tables": [],
        "extra_tables": [],
        "migration_mismatch": False,
    }

    # Get alembic head revision
    alembic_head = get_alembic_head_revision()
    result["alembic_head"] = alembic_head

    # Get current database revision
    db_revision = get_database_current_revision(sync_url)
    result["db_revision"] = db_revision

    # Check migration mismatch
    if alembic_head and db_revision and alembic_head != db_revision:
        result["migration_mismatch"] = True
        result["has_drift"] = True
        logger.warning(
            "Alembic revision mismatch: head=%s, db=%s", alembic_head, db_revision
        )

    # Check table differences
    model_tables = get_model_table_names()
    db_tables = get_database_table_names(sync_url)

    missing = model_tables - db_tables
    extra = db_tables - model_tables

    if missing:
        result["missing_tables"] = sorted(missing)
        result["has_drift"] = True
        logger.warning("Tables in models but missing in database: %s", sorted(missing))

    if extra:
        # Filter out alembic_version and test tables as they're expected
        extra_filtered = [t for t in extra if t not in {"alembic_version", "uow_test"}]
        if extra_filtered:
            result["extra_tables"] = sorted(extra_filtered)
            result["has_drift"] = True
            logger.warning("Extra tables in database not in models: %s", sorted(extra_filtered))

    return result


def assert_no_schema_drift(sync_url: Optional[str] = None) -> None:
    """
    Assert that there is no schema drift. Raises RuntimeError if drift detected.

    Use in CI/CD pipelines to fail fast on schema inconsistencies.
    """
    drift_info = check_schema_drift(sync_url)
    if drift_info["has_drift"]:
        error_msg = "Schema drift detected:\n"
        if drift_info["migration_mismatch"]:
            error_msg += (
                f"  - Alembic revision mismatch: head={drift_info['alembic_head']}, "
                f"db={drift_info['db_revision']}\n"
            )
        if drift_info["missing_tables"]:
            error_msg += f"  - Missing tables: {drift_info['missing_tables']}\n"
        if drift_info["extra_tables"]:
            error_msg += f"  - Extra tables: {drift_info['extra_tables']}\n"
        raise RuntimeError(error_msg)

    logger.info("Schema drift check passed: no drift detected")