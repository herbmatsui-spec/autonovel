"""
InfraContainer - インフラストラクチャ層のDIコンテナ
config.container.Container の責務を引き継ぎ、DB・設定・ベクトルストア等を提供する。
"""

from __future__ import annotations

import asyncio
import logging
import os

from dependency_injector import containers, providers

from config.constants import DATABASE_URL
from config.project_context import GlobalConfig
from schemas.config import GlobalConfigModel
from src.backend.database.core import DatabaseManager

# SPI ファクトリー
from src.core.spi.llm.provider_factory import LLMProviderFactory
from src.core.spi.vector_store.provider_factory import VectorStoreFactory
from src.core.spi.image.provider_factory import ImageProviderFactory

logger = logging.getLogger(__name__)


class InfraContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src", "src.kernels", "prompts"])

    config: providers.Singleton = providers.Singleton(GlobalConfigModel.load)

    global_config: providers.Singleton = providers.Singleton(GlobalConfig)

    db: providers.Singleton = providers.Singleton(
        DatabaseManager,
        db_url=providers.Callable(lambda: os.getenv("DATABASE_URL") or DATABASE_URL),
    )

    chroma_client_provider: providers.Singleton = providers.Singleton(
        "src.services.vector_store.ChromaClientProvider",
        db_path="./chroma_db",
    )

    vector_store: providers.Singleton = providers.Singleton(
        "src.services.vector_store.ChromaVectorStore",
        client_provider=chroma_client_provider,
    )

    audit_logger: providers.Singleton = providers.Singleton(lambda: None)

    cooldown: providers.Singleton = providers.Singleton(
        "src.backend.engine_utils.AdaptiveCooldown",
        base_sec=2.0,
        min_sec=0.5,
        max_sec=10.0,
    )

    max_concurrent_api_calls: providers.Singleton = providers.Singleton(
        lambda c: c.max_concurrent_api_calls,
        config,
    )

    concurrency_semaphore: providers.Singleton = providers.Singleton(
        asyncio.Semaphore,
        max_concurrent_api_calls,
    )

    # SPI ファクトリーの登録
    llm_provider_factory: providers.Singleton = providers.Singleton(LLMProviderFactory)
    vector_store_provider_factory: providers.Singleton = providers.Singleton(VectorStoreFactory)
    image_provider_factory: providers.Singleton = providers.Singleton(ImageProviderFactory)


__all__ = ["InfraContainer"]