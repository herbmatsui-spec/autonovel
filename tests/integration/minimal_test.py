"""Minimal test to check container access."""
from __future__ import annotations

import pytest


def test_minimal_chromadb(chadb_container):
    """Minimal test for ChromaDB container."""
    print("Container host:", chadb_container.get_container_host_ip())