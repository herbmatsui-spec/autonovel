"""Test to check if postgres fixture via DockerContainer works."""
from __future__ import annotations

import pytest


def test_postgres_via_docker(postgres_via_docker):
    """Just check that we get the postgres fixture via DockerContainer."""
    print("Type of postgres_via_docker:", type(postgres_via_docker))
    print("Postgres via Docker container:", postgres_via_docker)