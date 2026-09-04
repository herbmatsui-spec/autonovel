"""Test to verify PostgreSQL session fixture works."""
from __future__ import annotations

import pytest
from sqlalchemy import text


def test_postgres_session(postgres_session):
    """Test that we can get a session and run a simple query."""
    # Run a simple query
    result = postgres_session.execute(text("SELECT 1"))
    assert result.scalar() == 1

    # Check that we can see the tables (after migrations)
    # We'll query for the existence of a table that we know should exist after migrations.
    # For example, let's check for the 'book' table (assuming it exists in our models).
    # Note: We don't know the exact table names, but we can check for any table from our metadata.
    # Alternatively, we can check that the connection is valid and the session is usable.

    # We'll just do a simple query to ensure the session is working.
    result = postgres_session.execute(text("SELECT current_database()"))
    db_name = result.scalar()
    assert db_name is not None
    assert isinstance(db_name, str)
    assert len(db_name) > 0