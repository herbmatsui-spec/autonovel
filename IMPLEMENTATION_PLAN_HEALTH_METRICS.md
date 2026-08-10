# 実装計画書: ヘルスチェック拡張 + Prometheus メトリクス公開

## 概要
現在の `/health` エンドポイントを拡張し、DB・Redis・ChromaDB・LLM Gateway の疎通確認を含める。また、Prometheus 形式（`/metrics`）でメトリクスを公開する。

## 現状分析

### 既存の `/health` (src/backend/routers/health.py)
- DB 接続チェック（SQLAlchemy `SELECT 1`）
- Huey ワーカー状態・バックエンド種類・キュー深度
- レスポンス: `{"status": "ok", "database": "...", "worker": "...", "huey_backend": "...", "queue_depth": N}`

### 既存の `/metrics/huey-sqlite-busy` (src/backend/routers/metrics.py)
- Huey SQLite busy 状態の簡易プロキシ（プレースホルダー実装）
- JSON 形式のみ、Prometheus テキスト形式非対応

### 不足しているもの
1. Redis 疎通確認
2. ChromaDB 疎通確認
3. LLM Gateway (Gemini API) 疎通確認
4. Prometheus 標準形式 (`/metrics`) でのメトリクス公開
5. アプリケーション固有メトリクス（リクエスト数、レイテンシ、エラー率、生成タスク数等）

---

## 実装設計

### 1. 拡張ヘルスチェックレスポンス仕様

```json
{
  "status": "ok" | "degraded" | "unhealthy",
  "version": "3.0.0",
  "timestamp": "2026-08-08T01:44:30Z",
  "checks": {
    "database": {"status": "ok", "latency_ms": 12, "details": "pool=10/30"},
    "redis": {"status": "ok", "latency_ms": 3, "details": "connected_clients=5"},
    "chromadb": {"status": "ok", "latency_ms": 8, "details": "collections=3"},
    "llm_gateway": {"status": "ok", "latency_ms": 245, "details": "model=gemini-3.1-flash-lite"},
    "worker": {"status": "ok", "details": "huey_backend=redis, queue_depth=0"}
  }
}
```

- **status 判定ロジック**:
  - 全 check が `ok` → `ok`
  - いずれかが `degraded`（高レイテンシ等）→ `degraded`
  - いずれかが `error` → `unhealthy`

### 2. Prometheus メトリクス設計

#### 標準メトリクス (FastAPI + Prometheus Client)
| メトリクス名 | タイプ | 説明 |
|-------------|--------|------|
| `http_requests_total` | Counter | HTTP リクエスト総数 (method, path, status) |
| `http_request_duration_seconds` | Histogram | リクエストレイテンシ (method, path) |
| `http_requests_in_progress` | Gauge | 進行中リクエスト数 |

#### アプリケーション固有メトリクス
| メトリクス名 | タイプ | 説明 |
|-------------|--------|------|
| `novel_generation_tasks_total` | Counter | 生成タスク総数 (status: started/completed/failed) |
| `novel_generation_duration_seconds` | Histogram | 生成完了までの所要時間 (workflow_type) |
| `llm_api_calls_total` | Counter | LLM API 呼び出し数 (model, status) |
| `llm_api_tokens_total` | Counter | 使用トークン数 (model, type: prompt/completion) |
| `db_pool_connections_active` | Gauge | DB 接続プール使用中数 |
| `db_pool_connections_idle` | Gauge | DB 接続プールアイドル数 |
| `huey_queue_depth` | Gauge | Huey キュー深度 |
| `huey_tasks_processed_total` | Counter | 処理済みタスク数 (status) |
| `chromadb_collections` | Gauge | ChromaDB コレクション数 |
| `redis_connected_clients` | Gauge | Redis 接続クライアント数 |

---

## 実装手順

### Step 1: 依存関係追加
`requirements.txt` に追加:
```
prometheus-client>=0.19.0
redis>=5.0.0  # 既存
```

### Step 2: ヘルスチェック共通モジュール作成
**新規作成**: `src/backend/health/checks.py`
- 各依存サービスのチェック関数を定義
- 共通の `HealthCheckResult` データクラス
- タイムアウト・リトライ設定

### Step 3: `/health` エンドポイント拡張
**修正**: `src/backend/routers/health.py`
- `checks.py` の関数を使用
- レスポンスモデルを Pydantic で定義
- 総合ステータス判定ロジック実装

### Step 4: Prometheus メトリクス基盤構築
**新規作成**: `src/backend/observability/metrics.py`
- `prometheus_client` ベースのメトリクス定義
- FastAPI ミドルウェアで HTTP メトリクス自動収集
- メトリクス公開エンドポイント `/metrics` 追加

### Step 5: アプリケーション固有メトリクス計装
- **DB プール**: `DatabaseManager` に Gauge 更新フック追加
- **Huey**: タスク実行前後で Counter/Histogram 更新
- **LLM Gateway**: 呼び出しラッパーでメトリクス記録
- **ChromaDB/Redis**: ヘルスチェック時に Gauge 更新

### Step 6: サーバー統合
**修正**: `src/backend/server.py`
- `/metrics` ルーター登録
- HTTP メトリクスミドルウェア追加

### Step 7: テスト作成
**新規作成**: `tests/test_health.py`, `tests/test_metrics.py`
- ヘルスチェック各コンポーネントのモックテスト
- メトリクスエンドポイントのフォーマット検証
- 統合テスト (Testcontainers で Redis/PostgreSQL)

---

## ファイル構成（変更予定）

```
src/backend/
├── health/
│   ├── __init__.py
│   └── checks.py              # NEW: ヘルスチェック共通ロジック
├── observability/
│   ├── __init__.py
│   └── metrics.py             # NEW: Prometheus メトリクス定義
├── routers/
│   ├── health.py              # MODIFY: 拡張ヘルスチェック
│   └── metrics.py             # MODIFY: /metrics エンドポイント追加
├── database/
│   └── core.py                # MODIFY: DB プールメトリクスフック
├── tasks.py                   # MODIFY: Huey タスクメトリクス
└── server.py                  # MODIFY: ミドルウェア・ルーター登録
tests/
├── test_health.py             # NEW
└── test_metrics.py            # NEW
requirements.txt               # MODIFY: prometheus-client 追加
```

---

## 実装詳細

### `src/backend/health/checks.py`

```python
from dataclasses import dataclass
from enum import Enum
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"

@dataclass
class HealthCheckResult:
    status: HealthStatus
    latency_ms: Optional[float] = None
    details: str = ""
    error: str = ""

async def check_database(db_manager) -> HealthCheckResult:
    """DB 接続プールから接続取得 + SELECT 1"""
    start = time.perf_counter()
    try:
        from sqlalchemy import text
        async with db_manager.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        pool = db_manager.engine.pool
        return HealthCheckResult(
            status=HealthStatus.OK,
            latency_ms=latency,
            details=f"pool={pool.checkedin()}/{pool.size()}"
        )
    except Exception as e:
        logger.warning(f"DB health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))

async def check_redis(redis_url: str) -> HealthCheckResult:
    """Redis PING + INFO clients"""
    if not redis_url:
        return HealthCheckResult(status=HealthStatus.ERROR, error="REDIS_URL not configured")
    start = time.perf_counter()
    try:
        import redis.asyncio as redis
        client = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        await client.ping()
        info = await client.info("clients")
        await client.close()
        latency = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            status=HealthStatus.OK,
            latency_ms=latency,
            details=f"connected_clients={info.get('connected_clients', '?')}"
        )
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))

async def check_chromadb() -> HealthCheckResult:
    """ChromaDB ハートビート + コレクション一覧"""
    start = time.perf_counter()
    try:
        from src.core.container import AppContainer as Container
        client = Container.chroma_client_provider()
        if not client:
            return HealthCheckResult(status=HealthStatus.ERROR, error="ChromaDB not initialized")
        client.heartbeat()
        collections = client.list_collections()
        latency = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            status=HealthStatus.OK,
            latency_ms=latency,
            details=f"collections={len(collections)}"
        )
    except Exception as e:
        logger.warning(f"ChromaDB health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))

async def check_llm_gateway(api_key: str) -> HealthCheckResult:
    """LLM Gateway 軽量呼び出し（モデル一覧 or 短い生成）"""
    if not api_key or api_key == "DUMMY":
        return HealthCheckResult(status=HealthStatus.ERROR, error="API key not configured")
    start = time.perf_counter()
    try:
        from src.core.llm_gateway import LLMProviderFactory, create_genai_client
        genai_client = create_genai_client(api_key=api_key)
        factory = LLMProviderFactory(genai_client=genai_client)
        # ごく短いテスト生成（1 token 程度）
        result = await factory.generate_text(
            model="gemini-3.5-flash-lite",
            prompt="ping",
            max_tokens=1,
            temperature=0.0
        )
        latency = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            status=HealthStatus.OK if result else HealthStatus.ERROR,
            latency_ms=latency,
            details=f"model=gemini-3.5-flash-lite, response_len={len(result) if result else 0}"
        )
    except Exception as e:
        logger.warning(f"LLM Gateway health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))

async def check_worker() -> HealthCheckResult:
    """Huey ワーカー状態"""
    try:
        from src.backend.tasks import huey
        backend_class = huey.backend.__class__.__name__ if hasattr(huey, 'backend') else "unknown"
        huey_backend = "redis" if "Redis" in backend_class else "sqlite" if "Sqlite" in backend_class else "unknown"
        queue_depth = huey.pending_count()
        return HealthCheckResult(
            status=HealthStatus.OK,
            details=f"huey_backend={huey_backend}, queue_depth={queue_depth}"
        )
    except Exception as e:
        logger.warning(f"Worker health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))
```

### `src/backend/routers/health.py` (拡張版)

```python
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Dict, Optional
from src.core.container import AppContainer as Container
from src.backend.health.checks import (
    check_database, check_redis, check_chromadb, 
    check_llm_gateway, check_worker, HealthStatus, HealthCheckResult
)
from config import get_config

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])

class CheckResponse(BaseModel):
    status: HealthStatus
    latency_ms: Optional[float] = None
    details: str = ""
    error: str = ""

class HealthResponse(BaseModel):
    status: HealthStatus
    version: str = "3.0.0"
    timestamp: str
    checks: Dict[str, CheckResponse]

def determine_overall_status(checks: Dict[str, HealthCheckResult]) -> HealthStatus:
    statuses = [c.status for c in checks.values()]
    if HealthStatus.ERROR in statuses:
        return HealthStatus.ERROR
    if HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    return HealthStatus.OK

@router.get("/health", response_model=HealthResponse)
async def health_check():
    from datetime import datetime, timezone
    import asyncio
    
    cfg = get_config()
    
    # 並列実行でレイテンシ短縮
    db_manager = Container.db()
    results = await asyncio.gather(
        check_database(db_manager),
        check_redis(cfg.redis_url),
        check_chromadb(),
        check_llm_gateway(cfg.openai_api_key),
        check_worker(),
        return_exceptions=True
    )
    
    check_names = ["database", "redis", "chromadb", "llm_gateway", "worker"]
    checks = {}
    for name, result in zip(check_names, results):
        if isinstance(result, Exception):
            checks[name] = CheckResponse(status=HealthStatus.ERROR, error=str(result))
        elif isinstance(result, HealthCheckResult):
            checks[name] = CheckResponse(
                status=result.status,
                latency_ms=result.latency_ms,
                details=result.details,
                error=result.error
            )
        else:
            checks[name] = CheckResponse(status=HealthStatus.ERROR, error="Unexpected result type")
    
    overall = determine_overall_status({
        k: HealthCheckResult(status=v.status, latency_ms=v.latency_ms, details=v.details, error=v.error)
        for k, v in checks.items()
    })
    
    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks
    )
```

### `src/backend/observability/metrics.py`

```python
"""
Prometheus メトリクス定義・公開
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time
from functools import wraps
from typing import Callable, Any

# ===================== 標準 HTTP メトリクス =====================
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "path"]
)

# ===================== アプリ固有メトリクス =====================
novel_generation_tasks_total = Counter(
    "novel_generation_tasks_total",
    "Total novel generation tasks",
    ["workflow_type", "status"]  # status: started, completed, failed
)

novel_generation_duration_seconds = Histogram(
    "novel_generation_duration_seconds",
    "Novel generation duration in seconds",
    ["workflow_type"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
)

llm_api_calls_total = Counter(
    "llm_api_calls_total",
    "Total LLM API calls",
    ["model", "status"]  # status: success, error, timeout
)

llm_api_tokens_total = Counter(
    "llm_api_tokens_total",
    "Total LLM tokens used",
    ["model", "type"]  # type: prompt, completion
)

db_pool_connections_active = Gauge(
    "db_pool_connections_active",
    "Active database connections in pool"
)

db_pool_connections_idle = Gauge(
    "db_pool_connections_idle",
    "Idle database connections in pool"
)

huey_queue_depth = Gauge(
    "huey_queue_depth",
    "Huey task queue depth"
)

huey_tasks_processed_total = Counter(
    "huey_tasks_processed_total",
    "Total Huey tasks processed",
    ["status"]  # success, error, retry
)

chromadb_collections = Gauge(
    "chromadb_collections",
    "Number of ChromaDB collections"
)

redis_connected_clients = Gauge(
    "redis_connected_clients",
    "Number of connected Redis clients"
)

# ===================== ユーティリティ =====================
def record_http_metrics(method: str, path: str, status: int, duration: float):
    http_requests_total.labels(method=method, path=path, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, path=path).observe(duration)

def record_generation_task(workflow_type: str, status: str, duration: float = None):
    novel_generation_tasks_total.labels(workflow_type=workflow_type, status=status).inc()
    if duration is not None:
        novel_generation_duration_seconds.labels(workflow_type=workflow_type).observe(duration)

def record_llm_call(model: str, status: str, prompt_tokens: int = 0, completion_tokens: int = 0):
    llm_api_calls_total.labels(model=model, status=status).inc()
    if prompt_tokens:
        llm_api_tokens_total.labels(model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens:
        llm_api_tokens_total.labels(model=model, type="completion").inc(completion_tokens)

def update_db_pool_metrics(active: int, idle: int):
    db_pool_connections_active.set(active)
    db_pool_connections_idle.set(idle)

def update_huey_queue_depth(depth: int):
    huey_queue_depth.set(depth)

def record_huey_task(status: str):
    huey_tasks_processed_total.labels(status=status).inc()

def update_chromadb_collections(count: int):
    chromadb_collections.set(count)

def update_redis_clients(count: int):
    redis_connected_clients.set(count)

# ===================== /metrics エンドポイント用 =====================
async def metrics_endpoint() -> Response:
    """Prometheus メトリクス公開エンドポイント"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ===================== デコレータ（任意） =====================
def track_llm_metrics(model: str):
    """LLM 呼び出し関数をラップしてメトリクス記録"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                # result から token 数を取得できれば記録（実装依存）
                record_llm_call(model, "success")
                return result
            except Exception as e:
                record_llm_call(model, "error")
                raise
        return wrapper
    return decorator
```

### `src/backend/routers/metrics.py` (修正版)

```python
from fastapi import APIRouter
from src.backend.observability.metrics import metrics_endpoint

router = APIRouter(tags=["metrics"])

@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus 形式でメトリクスを公開"""
    return await metrics_endpoint()

# 既存の huey-sqlite-busy エンドポイントは互換性のため残却、非推奨化
@router.get("/metrics/huey-sqlite-busy", deprecated=True)
async def huey_sqlite_busy_metrics():
    """Deprecated: Use /metrics instead"""
    from src.backend.tasks import huey
    try:
        pending_count = huey.pending_count()
        backend_class = huey.backend.__class__.__name__ if hasattr(huey, 'backend') else "unknown"
        return {
            "huey_sqlite_busy_total": pending_count,
            "huey_backend": "sqlite" if "Sqlite" in backend_class else "redis" if "Redis" in backend_class else "unknown"
        }
    except Exception:
        return {"huey_sqlite_busy_total": 0, "huey_backend": "unknown"}
```

### `src/backend/server.py` への統合

```python
# 追加インポート
from src.backend.observability.metrics import (
    record_http_metrics, http_requests_in_progress
)

# HTTP メトリクスミドルウェア追加（create_app 内）
async def http_metrics_middleware(request: Request, call_next):
    method = request.method
    path = request.url.path
    http_requests_in_progress.labels(method=method, path=path).inc()
    start = time.perf_counter()
    try:
        response = await call_next(request)
        duration = time.perf_counter() - start
        record_http_metrics(method, path, response.status_code, duration)
        return response
    except Exception as e:
        duration = time.perf_counter() - start
        record_http_metrics(method, path, 500, duration)
        raise
    finally:
        http_requests_in_progress.labels(method=method, path=path).dec()

# ミドルウェア登録順序（外側から内側へ実行）
application.middleware("http")(http_metrics_middleware)  # 最外側で全リクエスト計測
application.middleware("http")(rate_limit_middleware)
application.middleware("http")(add_security_headers_middleware)
application.middleware("http")(add_trace_id_middleware)  # 最内側
```

---

## テスト計画

### 単体テスト (`tests/test_health.py`)
- 各チェック関数のモックテスト（正常・エラー・タイムアウト）
- 総合ステータス判定ロジックの境界値テスト

### 単体テスト (`tests/test_metrics.py`)
- `/metrics` レスポンスが Prometheus 形式でパース可能か
- 主要メトリクスが含まれるか
- HTTP メトリクスミドルウェアがカウント・ヒストグラム更新するか

### 統合テスト (`tests/integration/test_health_integration.py`)
- Testcontainers で Redis + PostgreSQL 起動
- 実際の依存サービスに対するヘルスチェック実行
- 障害注入（Redis 停止等）で `degraded`/`unhealthy` 判定確認

---

## ロールアウト手順

1. `requirements.txt` に `prometheus-client` 追加
2. 新規ファイル作成 (`health/checks.py`, `observability/metrics.py`)
3. 既存ファイル修正 (`routers/health.py`, `routers/metrics.py`, `server.py`)
4. 単体テスト実行 `pytest tests/test_health.py tests/test_metrics.py -v`
5. Docker ビルド・起動確認
6. `curl localhost:8200/health` と `curl localhost:8200/metrics` で動作確認
7. Grafana ダッシュボード雛形作成（別 PR で `monitoring/` に配置予定）

---

## リスク・注意点

| リスク | 対策 |
|--------|------|
| LLM Gateway チェックで API コスト発生 | 1 token のみ・キャッシュ可能・環境変数で無効化可 (`KAKU_HEALTH_CHECK_LLM=false`) |
| ChromaDB/Redis 未設定時のエラーハンドリング | 設定なし時は `ERROR` ではなく `NOT_CONFIGURED` 扱いにするか検討 |
| メトリクス公開によるパフォーマンス影響 | `prometheus_client` は軽量、ヒストグラムバケット調整で制御 |
| 既存 `/metrics/huey-sqlite-busy` の互換性 | `deprecated=True` で残し、ログで移行案内 |

---

## 完了基準

- [ ] `/health` が DB/Redis/ChromaDB/LLM/Worker 全てをチェックし、適切なステータス返却
- [ ] `/metrics` が Prometheus 形式で公開され、主要メトリクスが含まれる
- [ ] 単体テスト・統合テストが全パス
- [ ] Docker 環境で正常動作確認
- [ ] README にモニタリング項目追加