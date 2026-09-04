"""Standalone test with local fixture definition - simplified version."""
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
    assert chromadb_container is not None