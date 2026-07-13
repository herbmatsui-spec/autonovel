from dependency_injector import containers, providers

from config.base import DATABASE_URL
from config.project_context import GlobalConfig
from schemas.config import GlobalConfigModel
from src.backend.database.core import DatabaseManager


class Container(containers.DeclarativeContainer):
    # wiring設定
    wiring_config = containers.WiringConfiguration(packages=["src", "kernels", "prompts"])

    # 設定をシングルトンとして注入
    # GlobalConfigModel.load() は ConfigValidator.validate_all() に委譲（SSOT）
    config = providers.Singleton(GlobalConfigModel.load)

    # GlobalConfig をシングルトンとして注入
    global_config = providers.Singleton(GlobalConfig)

    # DatabaseManager をDIコンテナに統合
    db = providers.Singleton(DatabaseManager, db_url=DATABASE_URL)

    # ChromaDB クライアントプロバイダーをシングルトンとして注入
    chroma_client_provider = providers.Singleton(
        "src.services.vector_store.ChromaClientProvider",
        db_path="./chroma_db"
    )

    # VectorStore をDIコンテナに統合 (Provider経由)
    vector_store = providers.Singleton(
        "src.services.vector_store.ChromaVectorStore",
        client_provider=chroma_client_provider
    )


