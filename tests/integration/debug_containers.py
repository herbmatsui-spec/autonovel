"""Debug test to check container status."""
from __future__ import annotations

import pytest
from testcontainers.core.container import DockerContainer


def test_debug_chromadb_container(chadb_container):
    """Debug ChromaDB container configuration."""
    print(f"Container ID: {chadb_container.get_container_id()}")
    print(f"Container host IP: {chadb_container.get_container_host_ip()}")
    
    # Try to get exposed port with error handling
    try:
        port = chadb_container.get_exposed_port(8000)
        print(f"Exposed port 8000: {port}")
    except Exception as e:
        print(f"Error getting exposed port: {e}")
        
    # Try to get all exposed ports
    try:
        # This might not be available in all versions
        print("Trying to inspect container...")
        # Let's just see what attributes are available
        attrs = [attr for attr in dir(chadb_container) if not attr.startswith('_')]
        print(f"Available attributes: {attrs}")
    except Exception as e:
        print(f"Error inspecting container: {e}")