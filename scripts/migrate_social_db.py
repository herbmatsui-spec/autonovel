"""Database Migration and Verification Script for Social Dynamics and DAG State (Steps 61-62)."""
from __future__ import annotations

import argparse
import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect

from src.backend.database import engine
from src.backend.database.models import (
    Base,
    CharacterRelationship,
    CharacterJournal,
    CharacterComment,
    RelationshipHistory,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_social_db")


def check_and_create_tables() -> bool:
    """Verify that all social dynamics and task tables exist; create them if missing."""
    sync_engine = getattr(engine, "engine", engine)
    if hasattr(sync_engine, "sync_engine"):
        sync_engine = sync_engine.sync_engine

    inspector = inspect(sync_engine)
    existing_tables = set(inspector.get_table_names())
    logger.info(f"Existing tables in database: {len(existing_tables)}")

    required_tables = [
        "character_relationships",
        "character_journals",
        "character_comments",
        "relationship_histories",
    ]

    missing = [t for t in required_tables if t not in existing_tables]
    if missing:
        logger.info(f"Creating missing tables: {missing}")
        Base.metadata.create_all(bind=sync_engine)
        logger.info("All missing tables created successfully.")
    else:
        logger.info("All required social dynamics tables already exist.")

    # Re-inspect to verify
    inspector = inspect(sync_engine)
    final_tables = set(inspector.get_table_names())
    for t in required_tables:
        if t not in final_tables:
            logger.error(f"Table '{t}' failed to create!")
            return False

        # Inspect indexes
        indexes = inspector.get_indexes(t)
        logger.info(f"Table '{t}' verified. Indexes: {[idx['name'] for idx in indexes]}")

    logger.info("Migration & schema verification completed successfully!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Social DB Migration & Verification")
    parser.add_argument("--check-only", action="store_true", help="Only check tables without creating")
    args = parser.parse_args()

    success = check_and_create_tables()
    sys.exit(0 if success else 1)
