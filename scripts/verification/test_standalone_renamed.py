"""Standalone test with local fixture definition."""
from __future__ import annotations

import pytest
from testcontainers.core.container import DockerContainer


@pytest.fixture
def my_test_fixture():
    """Test fixture with different name."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


def test_with_different_fixture_name(my_test_fixture):
    """Test using fixture with different name."""
    print("Type of my_test_fixture:", type(my_test_fixture))
    print("My test fixture:", my_test_fixture)
    # Just check that we got the container
    assert my_test_fixture is not None
    container_id = my_test_fixture.get_container_id()
    assert container_id is not None
    print(f"Container ID: {container_id}")