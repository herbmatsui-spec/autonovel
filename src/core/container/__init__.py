import logging
import warnings

from dependency_injector import providers

# AppContainer は AppContainer2 のエイリアス（後方互換性のため）
from src.core.container.app import AppContainer2 as AppContainer
from src.core.container.infra import InfraContainer
from src.core.llm_gateway import LLMGenerateResultProxy

logger = logging.getLogger(__name__)


def make_container(api_key: str, db=None) -> AppContainer:
    """APIキーから AppContainer を生成する（非推奨）。
    代わりに AppContainer() を直接使用してください。
    """
    warnings.warn("use AppContainer instead", DeprecationWarning, stacklevel=2)
    if db is None:
        db = InfraContainer.db()
    return AppContainer(
        api_key=providers.Object(api_key),
        db=providers.Object(db) if db is not None else providers.Object(InfraContainer.db()),
    )


__all__ = [
    "AppContainer",
    "InfraContainer",
    "LLMGenerateResultProxy",
    "make_container",
]
