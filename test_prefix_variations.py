"""Standalone test with local fixture definition - testing prefix variations."""
from __future__ import annotations

import pytest
from testcontainers.core.container import DockerContainer


@pytest.fixture
def chadb_container():
    """The problematic name."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


@pytest.fixture
def chromad_container():
    """Missing the 'b'."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


@pytest.fixture
def chromab_container():
    """Missing the 'd'."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        yield chromadb


def test_chadb(chadb_container):
    """Test the original problematic name."""
    print("Testing chadb_container")
    assert chadb_container is not None


def test_chromad(chromad_container):
    """Test missing the 'b'."""
    print("Testing chromad_container")
    assert chromad_container is not None


def test_chromab(chromab_container):
    """Test missing the 'd'."""
    print("Testing chromab_container")
    assert chromab_container is not None