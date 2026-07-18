"""
InfraContainer - インフラストラクチャ層のDIコンテナ
config.container.Container の責務を引き継ぎ、DB・設定・ベクトルストア等を提供する。
"""
import logging

from dependency_injector import containers, providers

from config.base import DATABASE_URL
from config.project_context import GlobalConfig
from schemas.config import GlobalConfigModel
from src.backend.database.core import DatabaseManager

logger = logging.getLogger(__name__)


class InfraContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["src", "kernels", "prompts"]
    )

    config = providers.Singleton(GlobalConfigModel.load)

    global_config = providers.Singleton(GlobalConfig)

    db = providers.Singleton(
        DatabaseManager,
        db_url=DATABASE_URL,
    )

    chroma_client_provider = providers.Singleton(
        "src.services.vector_store.ChromaClientProvider",
        db_path="./chroma_db",
    )

    vector_store = providers.Singleton(
        "src.services.vector_store.ChromaVectorStore",
        client_provider=chroma_client_provider,
    )

    audit_logger = providers.Singleton(
        lambda: None
    )

    cooldown = providers.Singleton(
        "src.backend.engine_utils.AdaptiveCooldown",
        base_sec=2.0,
        min_sec=0.5,
        max_sec=10.0,
    )
