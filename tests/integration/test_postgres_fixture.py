"""Test to check if postgres fixture works."""
from __future__ import annotations

import pytest


def test_postgres_fixture(postgres_container):
    """Just check that we get the postgres fixture."""
    print("Type of postgres_container:", type(postgres_container))
    print("Postgres container:", postgres_container)