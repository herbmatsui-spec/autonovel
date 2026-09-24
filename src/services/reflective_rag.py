"""下位互換性維持のためのシム。実体は src.services.rag.reflective_rag に移動しました。"""
import warnings

warnings.warn(
    "src.services.reflective_rag is deprecated; use src.services.rag instead",
    DeprecationWarning,
    stacklevel=2,
)

from src.services.rag.reflective_rag import (  # noqa: F401
    ReflectiveRAGService,
    ReflectiveRetrievalResult,
    ConvergenceConfig,
    ContextFitResult,
    ReflectiveDoc,
)

__all__ = ["ReflectiveRAGService", "ReflectiveRetrievalResult", "ConvergenceConfig", "ContextFitResult", "ReflectiveDoc"]