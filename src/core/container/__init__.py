import logging
import warnings

from dependency_injector import providers

from src.core.container.infra import InfraContainer

logger = logging.getLogger(__name__)


def make_container(api_key: str, db=None):
    """APIキーから AppContainer を生成する（非推奨）。
    代わりに AppContainer() を直接使用してください。
    """
    warnings.warn("use AppContainer instead", DeprecationWarning, stacklevel=2)
    from src.core.container.app import AppContainer
    if db is None:
        db = InfraContainer.db()
    return AppContainer(
        api_key=providers.Object(api_key),
        db=providers.Object(db) if db is not None else providers.Object(InfraContainer.db()),
    )


def __getattr__(name: str):
    if name in ("AppContainer", "AppContainer2"):
        from src.core.container.app import AppContainer, AppContainer2
        return AppContainer if name == "AppContainer" else AppContainer2
    if name == "LLMGenerateResultProxy":
        from src.core.llm_gateway import LLMGenerateResultProxy
        return LLMGenerateResultProxy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AppContainer",
    "AppContainer2",
    "InfraContainer",
    "LLMGenerateResultProxy",
    "make_container",
]

