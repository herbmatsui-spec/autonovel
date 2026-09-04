"""Test to check if postgres fixture in integration/conftest.py works."""
from __future__ import annotations

import pytest


def test_postgres_fixture_integration(postgres_container):
    """Just check that we get the postgres fixture from integration/conftest.py."""
    print("Type of postgres_container:", type(postgres_container))
    print("Postgres container:", postgres_container)