"""Test to check if DockerContainer works directly in test."""
from __future__ import annotations

import pytest
from testcontainers.core.container import DockerContainer


def test_docker_container_direct():
    """Test using DockerContainer directly in test."""
    with DockerContainer("chromadb/chroma:latest") as chromadb:
        chromadb.with_exposed_ports(8000)
        # Just check that we got the container
        assert chromadb is not None
        container_id = chromadb.get_container_id()
        assert container_id is not None
        print(f"Container ID: {container_id}")