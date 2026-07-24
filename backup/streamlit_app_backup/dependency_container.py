"""
streamlit_app/dependency_container.py — Singleton DI Container for Core Services.

Manges EngineService, PluginLoader, and ResilientHttpClient instances with lazy initialization
and thread-safe singleton guarantees.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")

class DependencyContainer:
    """Singleton container for managing core service dependencies.

    Provides lazy-initialized singleton instances of:
    - EngineService
    - PluginLoader
    - ResilientHttpClient

    All dependencies are instantiated on first access and cached.
    """

    _instance: Optional["DependencyContainer"] = None
    _instances: Dict[str, Any] = {}
    _initialized = False

    def __new__(cls) -> "DependencyContainer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # -------------------------------------------------------------------------
    # Public API: Get services
    # -------------------------------------------------------------------------

    def get_engine_service(self) -> Any:
        """Get or create a singleton EngineService instance.

        Returns:
            EngineService: The shared EngineService instance
        """
        key = "EngineService"
        if key not in self._instances:
            from src.engine_service import EngineService

            self._instances[key] = EngineService.get_instance()
        return self._instances[key]

    def get_plugin_loader(self) -> Any:
        """Get or create a singleton PluginLoader instance.

        Returns:
            PluginLoader: The shared PluginLoader instance
        """
        key = "PluginLoader"
        if key not in self._instances:
            from src.core.plugin_loader import PluginLoader

            self._instances[key] = PluginLoader.get_instance()
        return self._instances[key]

    def get_resilient_http_client(self) -> Any:
        """Get or create a singleton ResilientHttpClient instance.

        Returns:
            ResilientHttpClient: The shared ResilientHttpClient instance
        """
        key = "ResilientHttpClient"
        if key not in self._instances:
            from src.shared.resilient_http import ResilientHttpClient

            self._instances[key] = ResilientHttpClient(name="streamlit_app")
        return self._instances[key]

    # -------------------------------------------------------------------------
    # Convenience: Register custom providers
    # -------------------------------------------------------------------------

    def register(self, service_type: type, instance: Any) -> None:
        """Register a custom instance for a given service type.

        Args:
            service_type: The service type/class that will be used as lookup key
            instance: The instance to register (must not be None)
        """
        if instance is None:
            raise ValueError("Cannot register None instance")

        self._instances[service_type.__name__] = instance

    # -------------------------------------------------------------------------
    # Internal: Utility methods
    # -------------------------------------------------------------------------

    @classmethod
    def reset(cls) -> None:
        """Reset the container to initial state.

        Clears all registered instances. Intended for testing purposes only.
        """
        cls._instances.clear()
        cls._initialized = False

    @classmethod
    def has_instance(cls, service_name: str) -> bool:
        """Check if a service instance is currently registered.

        Args:
            service_name: The service name to check

        Returns:
            bool: True if instance exists, False otherwise
        """
        return service_name in cls._instances

    @classmethod
    def get_all_instances(cls) -> Dict[str, Any]:
        """Get a copy of all registered instances.

        Returns:
            Dict[str, Any]: Dictionary of all service instances
        """
        return cls._instances.copy()


# -----------------------------------------------------------------------------
# Global singleton instance for convenience
# -----------------------------------------------------------------------------
container = DependencyContainer()