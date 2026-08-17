"""
InfraContainer - インフラストラクチャ層のDIコンテナ
config.container.Container の責務を引き継ぎ、DB・設定・ベクトルストア等を提供する。
"""

import asyncio
import logging

from dependency_injector import containers, providers

from config.settings import Settings, get_settings
from src.backend.database.core import DatabaseManager

logger = logging.getLogger(__name__)


class InfraContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src", "src.kernels", "prompts"])

    config = providers.Singleton(get_settings)

    global_config = providers.Singleton(
        "config.project_context.GlobalConfig",
    )

    db = providers.Singleton(
        DatabaseManager,
        db_url=providers.Callable(lambda c: c.database_url, config),
    )

    chroma_client_provider = providers.Singleton(
        "src.services.vector_store.ChromaClientProvider",
        db_path=providers.Callable(lambda c: str(c.chroma_db_path), config),
    )

    vector_store = providers.Singleton(
        "src.services.vector_store.ChromaVectorStore",
        client_provider=chroma_client_provider,
    )

    audit_logger = providers.Singleton(lambda: None)

    cooldown = providers.Singleton(
        "src.backend.engine_utils.AdaptiveCooldown",
        base_sec=2.0,
        min_sec=0.5,
        max_sec=10.0,
    )

    max_concurrent_api_calls = providers.Singleton(
        providers.Callable(lambda c: c.max_concurrent_api_calls, config),
    )

    concurrency_semaphore = providers.Factory(
        asyncio.Semaphore,
        max_concurrent_api_calls,
    )
