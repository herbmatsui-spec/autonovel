from dependency_injector import containers, providers

from config.base import DATABASE_URL
from config.project_context import GlobalConfig
from schemas.config import GlobalConfigModel
from src.backend.database.core import DatabaseManager
from src.services.vector_store import ChromaClientProvider, ChromaVectorStore


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src", "kernels", "prompts"])

    config = providers.Singleton(GlobalConfigModel.load)
    global_config = providers.Singleton(GlobalConfig)
    db = providers.Singleton(DatabaseManager, db_url=DATABASE_URL)
    chroma_client_provider = providers.Singleton(
        ChromaClientProvider,
        db_path="./chroma_db",
    )
    vector_store = providers.Singleton(
        ChromaVectorStore,
        client_provider=chroma_client_provider,
    )


_container_singleton = None


def get_container() -> Container:
    """InfraContainer の後方互換ラッパ。新規コードでは AppContainer を使用すること。"""
    global _container_singleton
    if _container_singleton is None:
        _container_singleton = Container()
    return _container_singleton


