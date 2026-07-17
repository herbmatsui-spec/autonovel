import logging

from dependency_injector import providers

from src.core.container.app import AppContainer2 as AppContainer
from src.core.container.infra import InfraContainer
from src.core.llm_gateway import LLMGenerateResultProxy

logger = logging.getLogger(__name__)

def make_container(api_key: str, db=None) -> AppContainer:
    """APIキーから AppContainer を生成する。
    
    Args:
        api_key: LLM クライアント用の API キー。
        db: 任意で外部の DatabaseManager を注入（InfraContainer の db を使用）。
    
    Returns:
        AppContainer インスタンス。初回生成時にログ出力。
    """
    if db is None:
        db = InfraContainer.db()
    container = AppContainer(
        api_key=providers.Object(api_key),
        db=providers.Object(db) if db is not None else providers.Object(InfraContainer.db()),
    )
    logger.info(f"Initialized AppContainer for api_key: {api_key[:4]}***")
    return container

__all__ = ["AppContainer", "AppContainer2", "InfraContainer", "LLMGenerateResultProxy", "make_container"]