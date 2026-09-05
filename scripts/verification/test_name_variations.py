"""Standalone test with local fixture definition - testing name variations."""
from __future__ import annotations

import pytest
from testcontainers.core.container import DockerContainer


@pytest.fixture
def chromadb_container():
    """Original name."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


@pytest.fixture
def chromadb_container_alt():
    """Alternative name with _alt suffix."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


@pytest.fixture
def chroma_db_container():
    """Name with underscore between chroma and db."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


def test_original_name(chadb_container):
    """Test using original name."""
    print("Testing original name: chromadb_container")
    assert chromadb_container is not None


def test_alt_name(chadb_container_alt):
    """Test using alternative name."""
    print("Testing alt name: chromadb_container_alt")
    assert chromadb_container_alt is not None


def test_underscore_name(chroma_db_container):
    """Test using underscore name."""
    print("Testing underscore name: chroma_db_container")
    assert chroma_db_container is not None