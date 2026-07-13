"""Engine helper functions."""
from src.backend.engine import UltimateHegemonyEngine
from config.container import Container

def get_engine(api_key: str) -> UltimateHegemonyEngine:
    """APIキーからエンジンインスタンスを生成する。"""
    from config.container import AppContainer
    from dependency_injector import providers
    container = AppContainer(
        api_key=providers.Object(api_key),
        db=providers.Object(Container.db())
    )
    return container.engine()
