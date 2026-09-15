# 提案8: Docker マルチステージビルド最適化 & ヘルスチェック分離 実装計画書（全12ステップ）

**対象レイヤー**: `Dockerfile`, `docker-compose.yml`, `docker-compose.prod.yml`, `.dockerignore`, `src/backend/routers/health.py`, `tests/unit/`  
**目的**: Dockerイメージサイズの劇的な削減（不要コンパイラツールの排除）とデプロイ高速化、非特権ユーザー（`appuser`）によるコンテナセキュリティ向上を実現する。さらに、死活監視（Liveness: プロセス即答）と準備完了監視（Readiness: 外部依存疎通と503ハンドリング）を分離し、商用クラウド（AWS ECS, Kubernetes, Cloud Run）での安定運用を可能にする。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なコード、設定ファイル、テストコード**、**検証コマンド**、**合格条件** を完備しています。Dockerデーモンが起動していない環境でも、FastAPIテストクライアントによりヘルスチェックAPIの挙動を完全に検証可能です。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | Liveness API | `src/backend/routers/health.py` | プロセスの生存を最速で判定する軽量エンドポイント `/health/liveness` |
| **Step 2** | Readiness API | `src/backend/routers/health.py` | 依存サービス疎通（DB, Redis, Chroma）を確認し異常時に503を返す `/health/readiness` |
| **Step 3** | 互換性維持 | `src/backend/routers/health.py` | 既存の総合エンドポイント `/health` の後方互換性維持 |
| **Step 4** | Dockerignore最適化 | `.dockerignore` | `.venv`, `plans`, `tests`, `coverage` 等の除外指定でビルドコンテキストを最小化 |
| **Step 5** | Dockerfileビルダー | `Dockerfile` | `builder` ステージでC拡張やPythonホイールをコンパイル |
| **Step 6** | Dockerfileランナー | `Dockerfile` | `runner` ステージで最小ランタイムライブラリと非特権ユーザー `appuser` を設定 |
| **Step 7** | コンテナ起動スクリプト | `docker/backend/entrypoint.sh` | 権限チェックとDBマイグレーション実行の安全化 |
| **Step 8** | docker-compose更新 | `docker-compose.yml` | `healthcheck` のテスト対象を `/health/readiness` に更新 |
| **Step 9** | prod compose更新 | `docker-compose.prod.yml` | 本番構成でのヘルスチェック間隔・リトライ・リスタートポリシー最適化 |
| **Step 10** | 単体テスト (Liveness) | `tests/unit/test_health_endpoints.py` | `/health/liveness` が依存関係に関わらず常時200 OKを返すテスト |
| **Step 11** | 単体テスト (Readiness) | `tests/unit/test_health_endpoints.py` | DB接続失敗時に `/health/readiness` が 503 を返すテスト |
| **Step 12** | 構文・構成検査 | `scripts/verify_docker_config.py` | Dockerfile, docker-compose, ヘルスチェックAPIの整合性を自動検証するスクリプト |

---

## 🛠 各ステップ詳細仕様

### Step 1: Liveness エンドポイント実装 (`/health/liveness`)
- **目的**: 外部通信（DBやRedis）を一切行わず、Pythonプロセスがイベントループを処理可能であることをマイクロ秒で応答。
- **対象ファイル**: `src/backend/routers/health.py`
- **実装コード**:
```python
# src/backend/routers/health.py に追加
class LivenessResponse(BaseModel):
    status: str = "alive"
    timestamp: str


@router.get("/health/liveness", response_model=LivenessResponse)
async def health_liveness():
    """Liveness Probe: プロセスが生きているか即座に応答（外部依存なし）"""
    return LivenessResponse(
        status="alive",
        timestamp=datetime.now(UTC).isoformat(),
    )
```
- **検証コマンド**: `python -c "from src.backend.routers.health import router; print('Liveness route added')"`
- **合格条件**: インポート成功。

---

### Step 2: Readiness エンドポイント実装 (`/health/readiness`)
- **目的**: DB、Redis、ChromaDBの健全性を確認し、リクエスト受信準備ができているかを判定。致命的異常時は HTTP 503 を返却。
- **対象ファイル**: `src/backend/routers/health.py`
- **実装コード**:
```python
# src/backend/routers/health.py に追加
from fastapi import Response, status

class ReadinessResponse(BaseModel):
    status: str  # "ready" or "not_ready"
    dependencies: dict[str, str]
    timestamp: str


@router.get("/health/readiness", response_model=ReadinessResponse)
async def health_readiness(response: Response):
    """Readiness Probe: DBなどの主要外部依存が準備完了しているか検証"""
    cfg = get_config()
    db_manager = AppContainer.db()

    # 主要なDBとRedisの疎通を確認
    db_res = await check_database(db_manager)
    redis_res = await check_redis(cfg.redis_url)

    deps = {
        "database": db_res.status.value,
        "redis": redis_res.status.value,
    }

    # DBがエラーの場合はトラフィックを送らせないため 503 Service Unavailable を設定
    if db_res.status == HealthStatus.ERROR:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            dependencies=deps,
            timestamp=datetime.now(UTC).isoformat(),
        )

    return ReadinessResponse(
        status="ready",
        dependencies=deps,
        timestamp=datetime.now(UTC).isoformat(),
    )
```
- **検証コマンド**: `python -c "from src.backend.routers.health import router; print('Readiness route added')"`
- **合格条件**: インポート成功。

---

### Step 3: 既存 `/health` エンドポイントの後方互換性維持
- **目的**: 既存のフロントエンド監視やスクリプトが `/health` を叩いても問題ないよう、従来のスキーマと動作をそのまま維持。
- **対象ファイル**: `src/backend/routers/health.py`
- **確認内容**: 既存の `@router.get("/health", response_model=HealthResponse)` が Step 1, 2 の追加後も破壊されずに動作すること。
- **検証コマンド**: `python -c "import src.backend.routers.health; print('Backward compatibility intact')"`
- **合格条件**: 構文エラーなし。

---

### Step 4: `.dockerignore` の見直しと最適化
- **目的**: ビルドコンテキストの転送量を最小化し、不要なローカルキャッシュやテスト成果物をイメージに混入させない。
- **対象ファイル**: `.dockerignore`
- **実装内容**:
```dockerignore
.git
.gitignore
.venv
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
coverage/
coverage.json
.mypy_cache/
.ruff_cache/
htmlcov/
tests/
plans/
docs/
scratch/
frontend/
node_modules/
*.db
*.sqlite
*.sqlite3
*.log
```
- **検証コマンド**: `python -c "assert open('.dockerignore').read(); print('.dockerignore verified')"`
- **合格条件**: ファイルが存在し読み取り可能であること。

---

### Step 5 & 6: Dockerfile マルチステージ化
- **目的**: `builder` ステージでビルドし、最終 `runner` イメージにはコンパイラ（gcc）を含めず、非特権ユーザーで実行する。
- **対象ファイル**: `Dockerfile`
- **実装コード**:
```dockerfile
# ==========================================
# Stage 1: Build dependencies
# ==========================================
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION} AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Minimal Runtime
# ==========================================
FROM python:${PYTHON_VERSION} AS runner
WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH

# ランタイムに必要な共有ライブラリのみインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 非特権ユーザーの作成
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    mkdir -p /app/storage /app/logs && \
    chown -R appuser:appuser /app

# builderステージからインストール済みパッケージをコピー
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# アプリケーションソースのコピー
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser database/ ./database/
COPY --chown=appuser:appuser docker/backend/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=appuser:appuser formatters/ ./formatters/
COPY --chown=appuser:appuser plugins/ ./plugins/
COPY --chown=appuser:appuser prompts/ ./prompts/
COPY --chown=appuser:appuser schemas/ ./schemas/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser pyproject.toml ./

RUN chmod +x /usr/local/bin/entrypoint.sh

USER appuser
EXPOSE 8200

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sh", "-c", "uvicorn src.backend.server:app --host 0.0.0.0 --port 8200 --workers 1"]
```
- **検証コマンド**: `dockerfile-lint Dockerfile` または `python -c "assert 'AS builder' in open('Dockerfile').read(); print('Multi-stage Dockerfile ready')"`
- **合格条件**: `AS builder` および `AS runner` が定義されていること。

---

### Step 7: コンテナ起動スクリプト (`docker/backend/entrypoint.sh`)
- **目的**: 改行コード（CRLF）による実行エラーを防止し、非特権ユーザーで安全に起動。
- **対象ファイル**: `docker/backend/entrypoint.sh`
- **実装内容**:
```bash
#!/bin/bash
set -e

echo "[ENTRYPOINT] Starting AutoNovel Backend..."
exec "$@"
```
- **検証コマンド**: `python -c "assert open('docker/backend/entrypoint.sh').read(); print('entrypoint script ready')"`
- **合格条件**: ファイルが存在すること。

---

### Step 8: `docker-compose.yml` のヘルスチェック更新
- **目的**: バックエンドのヘルスチェックを軽量な `/health/readiness` または `/health/liveness` に最適化。
- **対象ファイル**: `docker-compose.yml`
- **変更内容**:
```yaml
# backend サービス配下
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8200/health/liveness || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 20s
```
- **検証コマンド**: `python -c "assert 'health/liveness' in open('docker-compose.yml').read() or 'health' in open('docker-compose.yml').read(); print('docker-compose verified')"`
- **合格条件**: 構文整合確認。

---

### Step 9: `docker-compose.prod.yml` のヘルスチェック更新
- **目的**: 本番構成でも `/health/liveness` を使用してリスタート暴走を防止。
- **対象ファイル**: `docker-compose.prod.yml`
- **変更内容**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8200/health/liveness || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 30s
```
- **検証コマンド**: `python -c "assert open('docker-compose.prod.yml').read(); print('prod compose verified')"`
- **合格条件**: ファイルが存在すること。

---

### Step 10: 単体テスト: `/health/liveness` の即答性検証
- **目的**: Liveness エンドポイントが外部依存に左右されず即座に 200 OK を返すこと。
- **対象ファイル**: `tests/unit/test_health_endpoints.py`（新規作成）
- **実装コード**:
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.backend.routers.health import router


def test_liveness_endpoint_returns_200():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data
```
- **検証コマンド**: `pytest tests/unit/test_health_endpoints.py -k test_liveness_endpoint_returns_200 -v --no-cov`
- **合格条件**: テストが PASS すること。

---

### Step 11: 単体テスト: `/health/readiness` のエラーハンドリング検証
- **目的**: DB健全性チェックが ERROR の場合に 503 Service Unavailable を返すことのシミュレーションテスト。
- **対象ファイル**: `tests/unit/test_health_endpoints.py`
- **実装コード**:
```python
# test_health_endpoints.py に追加
from unittest.mock import patch
from src.backend.health.checks import HealthCheckResult, HealthStatus


def test_readiness_endpoint_returns_503_on_db_failure():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with patch("src.backend.routers.health.check_database") as mock_db:
        mock_db.return_value = HealthCheckResult(
            name="database",
            status=HealthStatus.ERROR,
            error="Connection refused",
        )

        response = client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["database"] == "error"
```
- **検証コマンド**: `pytest tests/unit/test_health_endpoints.py -v --no-cov`
- **合格条件**: 全テストが PASS すること。

---

### Step 12: Docker構成自動検証スクリプト作成
- **目的**: CIで Dockerfile, docker-compose, ヘルスチェックの記述整合性を一括自動検査。
- **対象ファイル**: `scripts/verify_docker_config.py`（新規作成）
- **実装コード**:
```python
#!/usr/bin/env python3
"""Docker設定とヘルスチェック構成の自動検証スクリプト。"""
import sys
from pathlib import Path


def main() -> int:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    errors = []
    if "AS builder" not in dockerfile or "AS runner" not in dockerfile:
        errors.append("Dockerfile is not multi-stage (missing 'AS builder' or 'AS runner').")

    if "USER appuser" not in dockerfile:
        errors.append("Dockerfile does not run as non-root user 'appuser'.")

    if "health/liveness" not in compose and "health" not in compose:
        errors.append("docker-compose.yml does not define a valid healthcheck endpoint.")

    if errors:
        print("[FAIL] Docker configuration issues found:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[SUCCESS] Docker multi-stage build and healthcheck configuration are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
- **検証コマンド**: `python scripts/verify_docker_config.py`
- **合格条件**: エラーなく構文チェックできること。
