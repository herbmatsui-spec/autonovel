from src.core.container import AppContainer


def test_container_basic_providers():
    container = AppContainer()
    assert container.api_key() == "DUMMY"
    assert container.cooldown() is not None
