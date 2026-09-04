"""Example showing how to migrate existing integration tests to use real PostgreSQL service."""
from __future__ import annotations

import pytest
from sqlalchemy import text


# This test shows how to migrate from using real_db_manager (SQLite) to postgres_session (PostgreSQL)
def test_example_migrated_to_postgres(postgres_session):
    """Example test showing usage of PostgreSQL session fixture.
    
    This demonstrates how existing tests that used real_db_manager can be migrated
    to use the PostgreSQL session fixture instead.
    """
    # Run a simple query to verify connection
    result = postgres_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    
    # The session can be used just like any SQLAlchemy session
    # For example, you could query tables that were created via metadata.create_all
    # in the postgres_engine fixture
    

# This test shows how to use the Redis container fixture
def test_example_redis_usage(redis_container):
    """Example test showing usage of Redis container fixture."""
    import redis
    
    # Get connection details from the container
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    
    # Create Redis client
    r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    
    # Test basic operations
    assert r.ping() is True
    r.set("example_key", "example_value")
    assert r.get("example_key") == "example_value"
    r.delete("example_key")
    r.close()


# This test shows how to use the ChromaDB container fixture
def test_example_chromadb_usage(chromadb_container):
    """Example test showing usage of ChromaDB container fixture."""
    import socket
    import time
    
    # Get connection details from the container
    chromadb_host = chromadb_container.get_container_host_ip()
    chromadb_port = chromadb_container.get_exposed_port(8000)
    
    # Wait a bit for ChromaDB to fully start up (additional safety)
    time.sleep(2)
    
    # Verify we can reach the container's exposed port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((chadb_host, int(chadb_port)))
    sock.close()
    assert result == 0, f"Cannot connect to ChromaDB at {chadb_host}:{chadb_port}"