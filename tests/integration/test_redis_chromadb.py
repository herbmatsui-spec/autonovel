"""Test to verify Redis and ChromaDB fixtures work."""
from __future__ import annotations

import pytest
import redis


def test_redis_container(redis_container):
    """Test that we can connect to Redis and run a simple command."""
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    assert r.ping() is True
    # Set and get a key
    r.set("test_key", "test_value")
    assert r.get("test_key") == "test_value"
    r.delete("test_key")
    r.close()


def test_chromadb_container(chromadb_container):
    """Test that we can connect to ChromaDB and get the version."""
    # We'll just check that the container is running and we can connect to the port
    import socket
    import time

    chromadb_host = chromadb_container.get_container_host_ip()
    chromadb_port = chromadb_container.get_exposed_port(8000)

    # Wait a bit for ChromaDB to fully start up
    time.sleep(3)

    # Verify we can reach the container's exposed port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((chadb_host, int(chadb_port)))
    sock.close()
    assert result == 0, f"Cannot connect to ChromaDB at {chadb_host}:{chadb_port}"