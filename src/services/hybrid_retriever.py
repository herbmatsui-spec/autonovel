"""下位互換性維持のためのシム。実体は src.services.rag.hybrid_retriever に移動しました。"""
import warnings

warnings.warn(
    "src.services.hybrid_retriever is deprecated; use src.services.rag instead",
    DeprecationWarning,
    stacklevel=2,
)

from src.services.rag.hybrid_retriever import HybridRetriever  # noqa: F401

__all__ = ["HybridRetriever"]