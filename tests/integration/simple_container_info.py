"""Simple test to get container info."""
from __future__ import annotations

import pytest
import time


def test_container_info(postgres_container, redis_container, chromadb_container):
    """Get basic info about containers."""
    print("=== PostgreSQL ===")
    print(f"Host: {postgres_container.get_container_host_ip()}")
    try:
        port = postgres_container.get_exposed_port(5432)
        print(f"Port 5432: {port}")
    except Exception as e:
        print(f"Error getting PG port: {e}")
    
    print("\n=== Redis ===")
    print(f"Host: {redis_container.get_container_host_ip()}")
    try:
        port = redis_container.get_exposed_port(6379)
        print(f"Port 6379: {port}")
    except Exception as e:
        print(f"Error getting Redis port: {e}")
    
    print("\n=== ChromaDB ===")
    print(f"Host: {chadb_container.get_container_host_ip()}")
    try:
        port = chadb_container.get_exposed_port(8000)
        print(f"Port 8000: {port}")
    except Exception as e:
        print(f"Error getting ChromaDB port: {e}")
        # Let's try to see what ports ARE exposed
        print("Container ID:", chadb_container.get_container_id())
