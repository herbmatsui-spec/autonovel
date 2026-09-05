"""Test to check if chromadb fixture works."""
from __future__ import annotations

import pytest


def test_chromadb_fixture(chadb_container):
    """Just check that we get the chromadb fixture."""
    print("Type of chromadb_container:", type(chadb_container))
    print("ChromaDB container:", chromadb_container)