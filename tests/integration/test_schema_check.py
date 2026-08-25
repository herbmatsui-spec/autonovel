"""
Integration test for schema drift detection.
"""
import pytest
import os

from src.backend.database.schema_check import check_schema_drift, assert_no_schema_drift


@pytest.mark.integration
def test_schema_drift_check():
    """Test that schema drift check runs without error."""
    # This test requires a database to be available
    # In CI, this will run against a test database
    result = check_schema_drift()
    # Just verify the function returns the expected structure
    assert "has_drift" in result
    assert "alembic_head" in result
    assert "db_revision" in result
    assert "missing_tables" in result
    assert "extra_tables" in result
    assert "migration_mismatch" in result


@pytest.mark.integration
def test_assert_no_schema_drift():
    """Test that assert_no_schema_drift doesn't raise when no drift."""
    # This will pass if schema is in sync
    try:
        assert_no_schema_drift()
    except RuntimeError as e:
        # If there's drift, the test should fail with the drift info
        pytest.fail(f"Schema drift detected: {e}")