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

def _get_chroma_client_provider():
    from src.services.vector_store.chroma import ChromaClientProvider
    return ChromaClientProvider(db_path="./chroma_db")


def _get_vector_store():
    from src.services.vector_store import get_default_store
    return get_default_store()


def _get_cooldown():
    from src.backend.engine_utils import AdaptiveCooldown
    return AdaptiveCooldown(base_sec=2.0, min_sec=0.5, max_sec=10.0)


class InfraContainer(containers.DeclarativeContainer):

    config: providers.Singleton = providers.Singleton(GlobalConfigModel.load)

    global_config: providers.Singleton = providers.Singleton(GlobalConfig)

    db: providers.Singleton = providers.Singleton(
        DatabaseManager,
        db_url=providers.Callable(lambda: os.getenv("DATABASE_URL") or DATABASE_URL),
    )

    chroma_client_provider: providers.Singleton = providers.Singleton(_get_chroma_client_provider)

    vector_store: providers.Singleton = providers.Singleton(_get_vector_store)

    audit_logger: providers.Singleton = providers.Singleton(lambda: None)

    cooldown: providers.Singleton = providers.Singleton(_get_cooldown)

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
