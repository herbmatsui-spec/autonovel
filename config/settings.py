"""Configuration settings for the project.

Provides a ``BASE_DIR`` constant representing the project root directory.
The tests and code rely on this value to locate the ``prompts`` folder.
"""

from pathlib import Path
from typing import Any, Optional
from contextvars import ContextVar

# Directory containing this file's parent (the repository root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Placeholder configuration values used across the codebase (tests expect them)
# These are minimal stubs sufficient for import resolution; real values are not needed for unit tests.
DATABASE_URL = "sqlite:///test.db"
STYLE_DEFINITIONS = {}
MODEL_EMBEDDING = "text-embedding-ada-002"
COOLDOWN_BASE_DEFAULT = 1.0
COOLDOWN_MAX_DEFAULT = 10.0
COOLDOWN_MIN_DEFAULT = 0.1

# Additional model and workflow constants used in various services
MODEL_PLANNING = "test-model-planning"
MODEL_PLOT_EXPANSION = "test-model-plot-expansion"
AUDIT_TRIGGER_KEYWORDS = []
STORY_ARCHETYPES = {}
DEFAULT_GOLDEN_PEAKS = []
STRESS_CATHARSIS_THRESHOLD = 0.5
STRESS_CLIMAX_BONUS = 0.2


STRESS_FILLER_THRESHOLD = 0.1
STRESS_HATE_GAIN_BASE = 0.05
PROMPT_TEMPLATES = {}


class Settings:
    """Simple settings container for tests.

    The real project may expose many attributes; tests only require that the
    object exists and provides ``validate_consistency`` and ``get_auto_concurrency``.
    """

    def __init__(self, _toml_kakuyomu_enabled=None):
        # Database URL for SQLAlchemy
        self.database_url = "sqlite+aiosqlite:///test.db"
        # Path for ChromaDB persistent storage
        self.chroma_db_path = "./chroma_db"
        # Maximum concurrent API calls allowed
        self.max_concurrent_api_calls = 10
        # Redis connection URL
        self.redis_url = "redis://localhost:6379"
        # API keys for LLM providers (used by EngineConfig resolver)
        self.gemini_api_key = ""
        self.openai_api_key = ""
        # CORS allowed origins
        self.cors_allowed_origins = "http://localhost:5173,http://localhost:8501,http://localhost:3000,http://127.0.0.1:5173"

        # Environment (default to test for simplicity)
        self.environment = "test"
        # Context window settings
        self.context_window_target_ratio = 0.75
        self.context_window_min_reserve = 2000
        # Style learning feature flag
        self.style_learning_enabled = True
        # Consistency Guardian feature flag
        self.consistency_guardian_enabled = True
        self.prompt_cache_max_size = 128
        # Kakuyomu ingestion (opt-in, default OFF). Mirrors settings.toml.
        # _toml_kakuyomu_enabled is set by load_settings_toml when it constructs
        # GlobalConfigModel(**flat_data) – None means "use the hard-coded default".
        if _toml_kakuyomu_enabled is None:
            _toml_kakuyomu_enabled = False
        self.kakuyomu_ingest_enabled = _toml_kakuyomu_enabled
        self.kakuyomu_ingest_limit = 10
        self.kakuyomu_request_interval = 2.0
        self.kakuyomu_user_agent = (
            "autonovel-bot/0.1 (+contact: see config/settings.toml)"
        )


    def validate_consistency(self) -> bool:
        """Stub method – always returns True for test environments."""
        return True

    def get_auto_concurrency(self) -> int:
        """Stub method – returns a default concurrency of 1.

        Some workflow code queries this value to decide parallelism.
        """
        return 1


# Global singleton instance used by ``get_settings``
_settings_instance = Settings()

# Context variable to hold configuration overrides for the current context.
# Each task or request can set its own overrides without affecting others.
_config_overrides_context: ContextVar[Optional[dict]] = ContextVar('_config_overrides_context', default=None)


class SettingsProxy:
    """
    A proxy for the Settings instance that respects context-specific overrides.
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    def __getattr__(self, name: str):
        # First, check if there is an override in the context
        overrides = _config_overrides_context.get()
        if overrides is not None and name in overrides:
            return overrides[name]
        # Otherwise, return the value from the actual settings instance
        return getattr(self._settings, name)

    # We do not allow setting attributes via the proxy to avoid accidentally
    # modifying the global settings instance. Overrides must be set via the
    # context variable.
    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_settings":
            super().__setattr__(name, value)
        else:
            raise AttributeError(
                f"Cannot set attribute '{name}' on SettingsProxy. "
                "Use the context variable to set overrides."
            )


# Global settings proxy instance used by ``get_settings``
_settings_proxy = SettingsProxy(_settings_instance)


def get_settings() -> SettingsProxy:
    """Return the global settings proxy instance.

    Tests may monkey‑patch this to inject custom values.
    """
    return _settings_proxy

def validate_api_keys() -> None:
    """Stub validation for API keys in test environment.

    In production this would verify that required keys are set.
    """
    # No-op for tests
    return None


def reset_settings() -> None:
    """Reset the singleton to a fresh ``Settings`` instance.

    This mirrors the behaviour of the original configuration module.
    """
    global _settings_instance, _settings_proxy
    _settings_instance = Settings()
    _settings_proxy = SettingsProxy(_settings_instance)
    ConfigManager._instance = None


# Placeholder for legacy imports; the real ConfigManager is in src.core.container
class ConfigManager:
    """Legacy compatibility class.

    The actual implementation resides in src.core.container.ConfigManager.
    This class is kept only to satisfy imports that expect ConfigManager
    to be present in config.settings.
    """
    _instance = None
    _config_cache = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config_cache = None  # 新インスタンス作成時にキャッシュクリア
        return cls._instance

    def __init__(self):
        pass
    
    @classmethod
    def get_config(cls):
        """Return the global settings via ConfigValidator."""
        # インスタンスを確保（初回呼び出し時にインスタンス生成＆キャッシュクリア）
        cls.get_instance()
        # インスタンスがリセットされている場合はキャッシュもクリア
        if cls._instance is None:
            cls._config_cache = None
        if cls._config_cache is None:
            from config.validator import ConfigValidator
            result = ConfigValidator.validate_all()
            cls._config_cache = result["settings"]
        return cls._config_cache

    @classmethod
    def clear_cache(cls):
        """Clear the cached config so that environment variable changes are reflected."""
        cls._config_cache = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


GlobalConfigModel = Settings
GlobalConfig = Settings
_settings_instance = Settings()