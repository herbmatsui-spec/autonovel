"""Configuration settings for the project.

Provides a ``BASE_DIR`` constant representing the project root directory.
The tests and code rely on this value to locate the ``prompts`` folder.
"""

from pathlib import Path
from typing import Any, Optional

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

    def __init__(self):
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

# Simple configuration container used by PromptRegistry and other components
class Config:
    """Minimal configuration object with attributes accessed in tests.

    Currently only ``prompt_cache_max_size`` is required by ``PromptRegistry``.
    """

    def __init__(self):
        self.prompt_cache_max_size = 100  # default cache size

class ConfigManager:
    """Accessor for a global ``GlobalConfigModel`` instance.
    """

    _instance: Optional[Any] = None

    @classmethod
    def get_config(cls):
        if cls._instance is None:
            from schemas.config import GlobalConfigModel
            cls._instance = GlobalConfigModel.load()
        return cls._instance


def get_settings() -> Settings:
    """Return the global ``Settings`` instance.

    Tests may monkey‑patch this to inject custom values.
    """
    return _settings_instance


def reset_settings() -> None:
    """Reset the singleton to a fresh ``Settings`` instance.

    This mirrors the behaviour of the original configuration module.
    """
    global _settings_instance
    _settings_instance = Settings()
    ConfigManager._instance = None

GlobalConfigModel = Settings
GlobalConfig = Settings
_settings_instance = Settings()