"""GraphRAG 用 Prometheus メトリクス定義.

Prometheus クライアントライブラリを使用して、GraphRAG 操作の
レイテンシ、スループット、エラー率、グラフサイズなどを監視する。

独自レジストリを使用してメインメトリクスとの重複登録を防止。
"""
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Info

# GraphRAG 専用レジストリ（メインメトリクスとの重複防止）
_graphrag_registry = CollectorRegistry()

def _get_registry() -> CollectorRegistry:
    """GraphRAG 専用レジストリを返す"""
    return _graphrag_registry

# ============================================================
# Graph 操作メトリクス
# ============================================================

GRAPH_OPERATIONS_TOTAL = Counter(
    "graph_operations_total",
    "Total number of graph operations",
    ["operation", "status"],
    registry=_graphrag_registry,
)

GRAPH_OPERATION_DURATION = Histogram(
    "graph_operation_duration_seconds",
    "Graph operation latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=_graphrag_registry,
)

GRAPH_NODES_TOTAL = Gauge(
    "graph_nodes_total",
    "Total number of nodes in the graph",
    ["graph_name", "label"],
    registry=_graphrag_registry,
)

GRAPH_EDGES_TOTAL = Gauge(
    "graph_edges_total",
    "Total number of edges in the graph",
    ["graph_name", "relation_type"],
    registry=_graphrag_registry,
)

GRAPH_GRAPHS_TOTAL = Gauge(
    "graph_graphs_total",
    "Total number of graphs",
    registry=_graphrag_registry,
)

# ============================================================
# Vector Store メトリクス
# ============================================================

VECTOR_STORE_OPERATIONS_TOTAL = Counter(
    "vector_store_operations_total",
    "Total number of vector store operations",
    ["backend", "operation", "status"],
    registry=_graphrag_registry,
)

VECTOR_STORE_OPERATION_DURATION = Histogram(
    "vector_store_operation_duration_seconds",
    "Vector store operation latency in seconds",
    ["backend", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=_graphrag_registry,
)

VECTOR_STORE_DOCUMENTS_TOTAL = Gauge(
    "vector_store_documents_total",
    "Total number of documents in vector store",
    ["backend", "collection_name"],
    registry=_graphrag_registry,
)

VECTOR_STORE_COLLECTIONS_TOTAL = Gauge(
    "vector_store_collections_total",
    "Total number of collections in vector store",
    ["backend"],
    registry=_graphrag_registry,
)

# ============================================================
# RAG メトリクス
# ============================================================

RAG_SEARCH_TOTAL = Counter(
    "rag_search_total",
    "Total number of RAG searches",
    ["search_type", "status"],
    registry=_graphrag_registry,
)

RAG_SEARCH_DURATION = Histogram(
    "rag_search_duration_seconds",
    "RAG search latency in seconds",
    ["search_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=_graphrag_registry,
)

RAG_RERANK_TOTAL = Counter(
    "rag_rerank_total",
    "Total number of reranking operations",
    ["backend", "status"],
    registry=_graphrag_registry,
)

RAG_RERANK_DURATION = Histogram(
    "rag_rerank_duration_seconds",
    "Reranking latency in seconds",
    ["backend"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=_graphrag_registry,
)

RAG_CONTEXT_BUILD_TOTAL = Counter(
    "rag_context_build_total",
    "Total number of RAG context builds",
    ["status"],
    registry=_graphrag_registry,
)

RAG_CONTEXT_BUILD_DURATION = Histogram(
    "rag_context_build_duration_seconds",
    "RAG context build latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=_graphrag_registry,
)

RAG_TOKEN_ESTIMATE = Histogram(
    "rag_token_estimate",
    "Estimated tokens in RAG context",
    buckets=[100, 250, 500, 1000, 2000, 4000, 8000, 16000],
    registry=_graphrag_registry,
)

RAG_CACHE_HITS = Counter(
    "rag_cache_hits_total",
    "Total number of RAG cache hits",
    ["cache_type"],
    registry=_graphrag_registry,
)

RAG_CACHE_MISSES = Counter(
    "rag_cache_misses_total",
    "Total number of RAG cache misses",
    ["cache_type"],
    registry=_graphrag_registry,
)

# ============================================================
# Pipeline メトリクス
# ============================================================

PIPELINE_CHAPTERS_PROCESSED = Counter(
    "pipeline_chapters_processed_total",
    "Total number of chapters processed by pipeline",
    ["status"],
    registry=_graphrag_registry,
)

PIPELINE_CHAPTERS_DURATION = Histogram(
    "pipeline_chapter_duration_seconds",
    "Pipeline chapter processing duration in seconds",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=_graphrag_registry,
)

PIPELINE_CHUNKS_CREATED = Counter(
    "pipeline_chunks_created_total",
    "Total number of chunks created by pipeline",
    registry=_graphrag_registry,
)

PIPELINE_ENTITIES_CREATED = Counter(
    "pipeline_entities_created_total",
    "Total number of entities created by pipeline",
    registry=_graphrag_registry,
)

PIPELINE_RELATIONSHIPS_CREATED = Counter(
    "pipeline_relationships_created_total",
    "Total number of relationships created by pipeline",
    registry=_graphrag_registry,
)

PIPELINE_IDEMPOTENCY_HITS = Counter(
    "pipeline_idempotency_hits_total",
    "Total number of idempotency key hits (skipped processing)",
    registry=_graphrag_registry,
)

PIPELINE_BATCH_PROCESSED = Counter(
    "pipeline_batch_processed_total",
    "Total number of batch processing runs",
    ["status"],
    registry=_graphrag_registry,
)

PIPELINE_BATCH_DURATION = Histogram(
    "pipeline_batch_duration_seconds",
    "Batch processing duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=_graphrag_registry,
)

# ============================================================
# Extraction メトリクス
# ============================================================

EXTRACTION_TOTAL = Counter(
    "extraction_total",
    "Total number of graph extractions",
    ["status"],
    registry=_graphrag_registry,
)

EXTRACTION_DURATION = Histogram(
    "extraction_duration_seconds",
    "Graph extraction latency in seconds",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=_graphrag_registry,
)

EXTRACTION_ENTITIES_EXTRACTED = Histogram(
    "extraction_entities_extracted",
    "Number of entities extracted per chapter",
    buckets=[1, 2, 5, 10, 20, 50, 100],
    registry=_graphrag_registry,
)

EXTRACTION_RELATIONSHIPS_EXTRACTED = Histogram(
    "extraction_relationships_extracted",
    "Number of relationships extracted per chapter",
    buckets=[0, 1, 2, 5, 10, 20, 50],
    registry=_graphrag_registry,
)

EXTRACTION_SELF_CORRECTION = Counter(
    "extraction_self_correction_total",
    "Total number of self-correction retries",
    registry=_graphrag_registry,
)

# ============================================================
# Embedding メトリクス
# ============================================================

EMBEDDING_GENERATION_TOTAL = Counter(
    "embedding_generation_total",
    "Total number of embedding generations",
    ["status"],
    registry=_graphrag_registry,
)

EMBEDDING_GENERATION_DURATION = Histogram(
    "embedding_generation_duration_seconds",
    "Embedding generation latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=_graphrag_registry,
)

EMBEDDING_BATCH_SIZE = Histogram(
    "embedding_batch_size",
    "Batch size for embedding generation",
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
    registry=_graphrag_registry,
)

EMBEDDING_DIMENSION = Gauge(
    "embedding_dimension",
    "Embedding vector dimension",
    registry=_graphrag_registry,
)

# ============================================================
# Database メトリクス
# ============================================================

DB_CONNECTION_POOL_SIZE = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    registry=_graphrag_registry,
)

DB_CONNECTION_POOL_CHECKED_OUT = Gauge(
    "db_connection_pool_checked_out",
    "Number of checked out connections",
    registry=_graphrag_registry,
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=_graphrag_registry,
)

DB_QUERY_ERRORS = Counter(
    "db_query_errors_total",
    "Total number of database query errors",
    ["operation", "error_type"],
    registry=_graphrag_registry,
)

# ============================================================
# LLM メトリクス
# ============================================================

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total number of LLM requests",
    ["provider", "model", "status"],
    registry=_graphrag_registry,
)

LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=_graphrag_registry,
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total number of tokens processed",
    ["provider", "model", "type"],
    registry=_graphrag_registry,
)

LLM_COST_TOTAL = Counter(
    "llm_cost_total_dollars",
    "Total estimated cost in USD",
    ["provider", "model"],
    registry=_graphrag_registry,
)

# ============================================================
# システム情報
# ============================================================

GRAPHRAG_INFO = Info(
    "graphrag_info",
    "GraphRAG system information",
    registry=_graphrag_registry,
)

def init_metrics():
    """メトリクス初期化（起動時呼び出し）"""
    GRAPHRAG_INFO.info({
        "version": "4.0.0",
        "components": "age,pgvector,rag,pipeline,extraction"
    })


def update_graph_stats(graph_name: str, node_count: int, edge_count: int, labels: list[str], rel_types: list[str]):
    """グラフ統計を更新"""
    GRAPH_GRAPHS_TOTAL.set(1)
    GRAPH_NODES_TOTAL.labels(graph_name=graph_name, label="all").set(node_count)
    GRAPH_EDGES_TOTAL.labels(graph_name=graph_name, relation_type="all").set(edge_count)

    for label in labels:
        GRAPH_NODES_TOTAL.labels(graph_name=graph_name, label=label).set(0)

    for rel_type in rel_types:
        GRAPH_EDGES_TOTAL.labels(graph_name=graph_name, relation_type=rel_type).set(0)


def update_vector_store_stats(backend: str, collection_name: str, doc_count: int):
    """ベクトルストア統計を更新"""
    VECTOR_STORE_DOCUMENTS_TOTAL.labels(backend=backend, collection_name=collection_name).set(doc_count)


def record_llm_cost(provider: str, model: str, cost_usd: float):
    """LLM コスト記録"""
    LLM_COST_TOTAL.labels(provider=provider, model=model).inc(cost_usd)


def get_metrics_summary() -> dict:
    """主要メトリクスのサマリーを取得（ヘルスチェック等で使用）"""
    from prometheus_client import REGISTRY

    summary = {}
    # GraphRAG 専用レジストリからも取得
    for registry in [REGISTRY, _graphrag_registry]:
        for metric in registry.collect():
            for sample in metric.samples:
                key = f"{sample.name}{{{','.join(f'{k}={v}' for k,v in sample.labels.items())}}}"
                summary[key] = sample.value
    return summary
