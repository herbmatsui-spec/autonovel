import logging
import os
from typing import Any, Dict, Tuple

import yaml

from .circuit_breaker import CircuitBreakerConfig
from .retry_policy import RetryPolicy

logger = logging.getLogger(__name__)

class ResilienceConfigLoader:
    """
    Loader for resilience configurations defined in YAML.
    Provides RetryPolicy and CircuitBreakerConfig for various services.
    """
    _instance = None
    _config_data: Dict[str, Any] = {}
    _config_path = "config/resilience.yaml"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResilienceConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Loads the YAML configuration file from disk."""
        if not os.path.exists(self._config_path):
            logger.warning(f"Resilience config file not found at {self._config_path}. Using defaults.")
            self._config_data = {}
            return

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
            logger.info(f"Successfully loaded resilience config from {self._config_path}")
        except Exception as e:
            logger.error(f"Error parsing resilience config: {e}. Using defaults.")
            self._config_data = {}

    def get_policy_for_service(self, service_name: str) -> Tuple[RetryPolicy, CircuitBreakerConfig]:
        """
        Retrieves the retry policy and circuit breaker config for a specific service.
        Falls back to 'default' settings if service-specific config is missing.
        """
        # 1. Get service-specific config or fall back to default
        services_config = self._config_data.get("services", {})
        service_settings = services_config.get(service_name, {})
        default_settings = self._config_data.get("default", {})

        # 2. Merge settings: Service specific > Default > DataClass defaults
        retry_data = {**default_settings.get("retry_policy", {}), **service_settings.get("retry_policy", {})}
        cb_data = {**default_settings.get("circuit_breaker", {}), **service_settings.get("circuit_breaker", {})}

        # 3. Instantiate data classes (filtering out None/invalid values)
        retry_policy = RetryPolicy(**{k: v for k, v in retry_data.items() if v is not None})
        cb_config = CircuitBreakerConfig(**{k: v for k, v in cb_data.items() if v is not None})

        return retry_policy, cb_config

# Global instance for easy access
resilience_config = ResilienceConfigLoader()
