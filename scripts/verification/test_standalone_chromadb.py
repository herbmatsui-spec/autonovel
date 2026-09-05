"""Standalone test with local fixture definition."""
from __future__ import annotations

import pytest
from testcontainers.core.container import DockerContainer


@pytest.fixture
def chromadb_container():
    """ChromaDB ファクスチャ (ローカル定義)."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


def test_chromadb_local_fixture(chadb_container):
    """Test using locally defined fixture."""
    print("Type of chromadb_container:", type(chadb_container))
    print("ChromaDB container:", chromadb_container)
    # Just check that we got the container
    assert chromadb_container is not None
    container_id = chromadb_container.get_container_id()
    assert container_id is not None
    print(f"Container ID: {container_id}")