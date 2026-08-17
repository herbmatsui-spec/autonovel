import os
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-dev")

from src.core.container import AppContainer


def test_container_basic_providers():
    container = AppContainer()
    assert container.api_key() == "test-key-for-dev"
    assert container.cooldown() is not None
