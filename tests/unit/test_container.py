from src.core.container import AppContainer


def test_app_container_instantiation():
    """AppContainer のインスタンス化と基本プロバイダの検証。"""
    container = AppContainer()
    assert container is not None
    assert hasattr(container, "repo")
    assert hasattr(container, "uow")


def test_app_container_override():
    """プロバイダのオーバーライド機能の検証。"""
    container = AppContainer()
    container.api_key.override("TEST_KEY_12345")

    assert container.api_key() == "TEST_KEY_12345"
    container.api_key.reset_override()
