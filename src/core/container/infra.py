"""
InfraContainer - インフラストラクチャ層のDIコンテナ
config.container.Container の責務を引き継ぎ、DB・設定・ベクトルストア等を提供する。
"""

import asyncio
import logging

from dependency_injector import containers, providers

from config.constants import DATABASE_URL
from config.project_context import GlobalConfig
from schemas.config import GlobalConfigModel
from src.backend.database.core import DatabaseManager

logger = logging.getLogger(__name__)


class InfraContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src", "src.kernels", "prompts"])

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

    audit_logger = providers.Singleton(lambda: None)

    cooldown = providers.Singleton(
        "src.backend.engine_utils.AdaptiveCooldown",
        base_sec=2.0,
        min_sec=0.5,
        max_sec=10.0,
    )

    max_concurrent_api_calls = providers.Singleton(
        lambda c: c.max_concurrent_api_calls,
        config,
    )

    concurrency_semaphore = providers.Singleton(
        asyncio.Semaphore,
        max_concurrent_api_calls,
    )

# 後方互換エイリアス。
# ref: tests/unit/test_infra_container.py および一部レガシーコードは
#      infra 層のコンテナを `AppContainer` として参照する。
#      アプリ層 (agents/engine) の DI は src.core.container.app.AppContainer2 を
#      使うべきだが、infra 層だけを検証するテストのために infra.py にも
#      同名を公開する。InfraContainer のプロバイダ群をそのまま解決する。
