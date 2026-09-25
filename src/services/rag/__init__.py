"""RAG services package.

RAG関連機能の体系化:
- RAGPipelineService: 検索パイプラインのエントリポイント（GraphRAGService）
- ReflectiveRAGService: 反思的RAG検索
- HybridRetriever: ハイブリッド検索
- context_retriever: コンテキスト検索ユーティリティ
"""
from src.services.rag.rag_service import (
    GraphRAGService,
    rag_service,
    Reranker,
    SearchResult,
    RagContext,
)
from src.services.rag.reflective_rag import (
    ReflectiveRAGService,
    ReflectiveRetrievalResult,
    ConvergenceConfig,
    ContextFitResult,
    ReflectiveDoc,
)
from src.services.rag.hybrid_retriever import HybridRetriever
from src.services.rag.context_retriever import ForeshadowingEntity

# 検索パイプラインのエントリポイント
RAGPipelineService = GraphRAGService

__all__ = [
    "RAGPipelineService",
    "GraphRAGService",
    "rag_service",
    "Reranker",
    "SearchResult",
    "RagContext",
    "ReflectiveRAGService",
    "ReflectiveRetrievalResult",
    "ConvergenceConfig",
    "ContextFitResult",
    "ReflectiveDoc",
    "HybridRetriever",
    "ForeshadowingEntity",
]