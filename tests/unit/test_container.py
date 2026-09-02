from src.core.container import AppContainer, AppContainer2, InfraContainer


def test_app_container_instantiation():
    """AppContainer のインスタンス化と基本プロバイダの検証。"""
    container = AppContainer()
    assert container is not None
    assert hasattr(container, "repo")
    assert hasattr(container, "uow")
    assert hasattr(container, "db")
    assert hasattr(container, "auditor")
    assert AppContainer2 is AppContainer


def test_app_container_override():
    """プロバイダのオーバーライド機能の検証。"""
    container = AppContainer()
    container.api_key.override("TEST_KEY_12345")

    assert container.api_key() == "TEST_KEY_12345"
    container.api_key.reset_override()


def test_legacy_config_container_compatibility():
    """config.container の後方互換ラッパーの検証。"""
    from config.container import Container, get_container

    c1 = get_container()
    assert c1 is not None
    assert issubclass(Container, AppContainer)

