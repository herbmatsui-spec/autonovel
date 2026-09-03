# リグレッション防止 実装計画書

## 概要
GraphRAG / Apache AGE 統合実装完了後のリグレッション（品質劣化）を防止するための CI/CD、テスト、監視基盤を構築する。

---

## フェーズ 1: CI/CD パイプライン構築

### 1.1 GitHub Actions ワークフロー
**ファイル**: `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - name: Install dependencies
        run: |
          pip install -e ".[dev,rag]"
      - name: Run ruff
        run: python -m ruff check src/
      - name: Run mypy
        run: python -m mypy src/ --ignore-missing-imports

  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - name: Install dependencies
        run: pip install -e ".[dev,rag]"
      - name: Run unit tests
        run: python -m pytest tests/unit/ -v --tb=short -x

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: apache/age-postgresql:16-pgvector
        env:
          POSTGRES_USER: autonovel
          POSTGRES_PASSWORD: autonovel
          POSTGRES_DB: autonovel
        ports: ["5432:5432"]
        options: >-
          --health-cmd="pg_isready -U autonovel -d autonovel"
          --health-interval=5s
          --health-timeout=5s
          --health-retries=10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - name: Install dependencies
        run: pip install -e ".[dev,rag]"
      - name: Wait for PostgreSQL
        run: sleep 10
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://autonovel:autonovel@localhost:5432/autonovel
          ENABLE_GRAPHRAG: "true"
        run: python -m pytest tests/integration/test_graphrag_age.py -v --tb=short

  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - name: Install dependencies
        run: pip install -e ".[dev,rag]"
      - name: Run contract tests
        run: python -m pytest tests/contract/ -v --tb=short

  performance-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    services:
      postgres:
        image: apache/age-postgresql:16-pgvector
        env:
          POSTGRES_USER: autonovel
          POSTGRES_PASSWORD: autonovel
          POSTGRES_DB: autonovel
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -e ".[dev,rag]"
      - name: Run performance tests
        env:
          DATABASE_URL: postgresql://autonovel:autonovel@localhost:5432/autonovel
          ENABLE_GRAPHRAG: "true"
        run: python -m pytest tests/perf/ -v --tb=short -m perf
```

### 1.2 Pre-commit フック
**ファイル**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.5
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v2.3.1
    hooks:
      - id: mypy
        args: [--ignore-missing-imports, src/]
        additional_dependencies: [pydantic, sqlalchemy, fastapi]
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: python -m pytest tests/unit/ -q --tb=short
        language: system
        pass_filenames: false
        stages: [pre-push]
```

---

## フェーズ 2: 契約テスト（スキーマ・API 互換性）

### 2.1 Pydantic スキーマ契約テスト
**ファイル**: `tests/contract/test_graph_schemas.py`

### 2.2 API 契約テスト
**ファイル**: `tests/contract/test_api_contracts.py`

### 2.3 マイグレーション契約テスト
**ファイル**: `tests/test_migrations.py`

---

## フェーズ 3: パフォーマンス回帰テスト

### 3.1 パフォーマンステスト
**ファイル**: `tests/perf/test_performance_regression.py`

### 3.2 ベンチマーク基準値管理
**ファイル**: `tests/perf/benchmarks.json`

```json
{
  "age_upsert_1000_nodes_ms": 5000,
  "pgvector_search_1000_docs_ms": 100,
  "rag_hybrid_search_ms": 200,
  "pipeline_batch_10_chapters_ms": 30000
}
```

---

## フェーズ 4: 監視・メトリクス

### 4.1 Prometheus メトリクス定義
**ファイル**: `src/backend/observability/graph_metrics.py`

### 4.2 メトリクスエンドポイント追加
**ファイル**: `src/backend/routers/metrics.py` 更新

---

## フェーズ 5: ドキュメント同期・依存関係管理

### 5.1 API ルート自動ドキュメント生成
**ファイル**: `scripts/generate_api_docs.py`

### 5.2 Dependabot 設定
**ファイル**: `.github/dependabot.yml`

---

## 実装順序・優先度

| フェーズ | 優先度 | 見積工数 | 依存関係 |
|---------|--------|----------|----------|
| 1. CI/CD | P0 | 3h | なし |
| 2. 契約テスト | P0 | 2h | 1 |
| 3. パフォーマンステスト | P1 | 2h | 1 |
| 4. 監視メトリクス | P1 | 2h | なし |
| 5. ドキュメント・依存関係 | P2 | 1h | なし |

**合計: 約 10h**

---

## 受け入れ基準

1. **CI パス**: 全ワークフローが main ブランチでグリーン
2. **Pre-commit**: `pre-commit run --all-files` がエラーなし
3. **契約テスト**: スキーマ/API 破壊的変更でテスト失敗
4. **パフォーマンス**: ベンチマーク閾値超過でテスト失敗
5. **メトリクス**: `/metrics` エンドポイントで GraphRAG 指標取得可能
6. **ドキュメント**: API ルート変更時にドキュメント自動更新検知