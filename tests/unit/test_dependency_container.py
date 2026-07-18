"""
Integration tests for DependencyContainer.
"""
import pytest

from streamlit_app.dependency_container import DependencyContainer, container


class TestDependencyContainer:
    """Test DependencyContainer functionality."""

    def setup_method(self):
        """Reset container before each test."""
        DependencyContainer.reset()

    def test_singleton_pattern(self):
        """Test that container returns same instance on multiple calls."""
        from streamlit_app.dependency_container import DependencyContainer

        c1 = DependencyContainer()
        c2 = DependencyContainer()
        assert c1 is c2

    def test_get_engine_service(self):
        """Test EngineService retrieval."""
        service = container.get_engine_service()
        assert service is not None
        assert type(service).__name__ == "EngineService"

    def test_get_plugin_loader(self):
        """Test PluginLoader retrieval."""
        loader = container.get_plugin_loader()
        assert loader is not None
        assert type(loader).__name__ == "PluginLoader"

    def test_get_resilient_http_client(self):
        """Test ResilientHttpClient retrieval."""
        client = container.get_resilient_http_client()
        assert client is not None
        assert type(client).__name__ == "ResilientHttpClient"
        assert client.name == "streamlit_app"

    def test_has_instance(self):
        """Test has_instance method."""
        assert not DependencyContainer.has_instance("EngineService")
        container.get_engine_service()
        assert DependencyContainer.has_instance("EngineService")

    def test_reset(self):
        """Test reset clears all instances."""
        container.get_engine_service()
        container.get_plugin_loader()
        assert len(DependencyContainer.get_all_instances()) == 2

        DependencyContainer.reset()
        assert len(DependencyContainer.get_all_instances()) == 0
        assert not DependencyContainer.has_instance("EngineService")

    def test_register_custom_instance(self):
        """Test registering custom instances."""
        class MockService:
            pass

        mock = MockService()
        container.register(MockService, mock)
        assert DependencyContainer.has_instance("MockService")

        retrieved = container._instances.get("MockService")
        assert retrieved is mock

    def test_get_all_instances_returns_copy(self):
        """Test that get_all_instances returns a copy with same data."""
        container.get_engine_service()
        instances1 = DependencyContainer.get_all_instances()
        instances2 = DependencyContainer.get_all_instances()
        assert instances1 == instances2  # Should have equal content
        assert instances1 is not instances2  # But different objects (copies)
        assert len(instances1) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
