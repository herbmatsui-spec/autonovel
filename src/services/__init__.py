"""AutoNovel ビジネスロジック・サービスパッケージ.

Phase 2 アーキテクチャ整理により集約された主要サービスを公開。
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.writing import WritingService, WritingServices
    from src.services.audit import AuditAggregatorService, AuditService
    from src.services.marketing import MarketingService
    from src.services.rag import (
        RAGPipelineService,
        GraphRAGService,
        ReflectiveRAGService,
        HybridRetriever,
    )
    from src.services.editor_assist_service import EditorAssistService
    from src.services.editorial_assistant_service import EditorialAssistantService
    from src.services.next_beats_service import NextBeatsService

# 動的遅延解決テーブル
_EXPORTS = {
    # Part 1: Writing
    "WritingService": ("src.domain.writing", "WritingService"),
    "WritingServices": ("src.domain.writing", "WritingServices"),
    # Part 4: Audit
    "AuditAggregatorService": ("src.services.audit", "AuditAggregatorService"),
    "AuditService": ("src.services.audit", "AuditService"),
    # Part 4: Marketing
    "MarketingService": ("src.services.marketing", "MarketingService"),
    # Part 4: RAG
    "RAGPipelineService": ("src.services.rag", "RAGPipelineService"),
    "GraphRAGService": ("src.services.rag", "GraphRAGService"),
    "ReflectiveRAGService": ("src.services.rag", "ReflectiveRAGService"),
    "HybridRetriever": ("src.services.rag", "HybridRetriever"),
    # Editor
    "EditorAssistService": ("src.services.editor_assist_service", "EditorAssistService"),
    "EditorialAssistantService": ("src.services.editorial_assistant_service", "EditorialAssistantService"),
    "NextBeatsService": ("src.services.next_beats_service", "NextBeatsService"),
}

__all__ = [
    "WritingService",
    "WritingServices",
    "AuditAggregatorService",
    "AuditService",
    "MarketingService",
    "RAGPipelineService",
    "GraphRAGService",
    "ReflectiveRAGService",
    "HybridRetriever",
    "EditorAssistService",
    "EditorialAssistantService",
    "NextBeatsService",
]


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        mod_name, attr_name = _EXPORTS[name]
        mod = importlib.import_module(mod_name)
        val = getattr(mod, attr_name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
