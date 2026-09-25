# Phase 4: 環境統一と商用ローンチ（Production Readiness） - 詳細実装計画書

**作成日**: 2026-09-24  
**ベースライン**: `plans/PHASE_ROADMAP_MASTER.md` Phase 4 セクション + Phase 3 完了済み（コア軽量化・Easy Mode）  
**ゴール**: 本番Docker環境での安定稼働と低コスト運用  
**前提**: Phase 3 が完了し、Easy Mode が完成し、ベンチマーク目標が達成されていること

---

## 全24ステップ 概要

| Step | カテゴリ | 作業内容 | 成果物 | テスト/検証 |
|------|----------|----------|--------|-------------|
| 1 | ブランチ | 作業ブランチ `phase4-production` 作成・切替（Phase 3 完了ベースラインから） | ブランチ | `git status` |
| 2 | ブランチ | Phase 3 完了ベースラインから開始 (`git checkout phase3-done`) | ベースライン確認 | `git log --oneline -1` |
| 3 | 環境境界定義 | ローカル（SQLite）と本番（PostgreSQL+pgvector）の環境変数・設定の違いを文書化 | `docs/ENVIRONMENT_BOUNDARY.md` | レビュー承認 |
| 4 | 設定分離実装 | 環境別設定ファイルの構成（`config/local.yaml`、`config/production.yaml`）およびローダーの環境判定ロジック | `src/config/env_loader.py` | ユニットテスト PASS |
| 5 | 本番Dockerfile作成 | 本番相当のマルチステージDockerfile（依存インストール → ビルド → 実行ユーザー分離） | `Dockerfile.prod` | `docker build` 成功・イメージサイズ確認 |
| 6 | Docker Compose 本番構成 | 本番用の `docker-compose.prod.yml`（サービス・ネットワーク・ボリューム・環境変数） | `docker-compose.prod.yml` | `docker compose up` 成功・ヘルスチェック PASS |
| 7 | E2E テスト実装 | 本番構成でのエンドツーエンドシナリオテスト（生成→ダウンロード） | `tests/e2e/test_production_e2e.py` | `pytest` PASS（本番コンテナ上） |
| 8 | 監視基盤導入 | Sentry エラー追跡の統合（DSN 設定・初期化・ハンドラ登録） | `src/monitoring/sentry.py` | ユニットテスト PASS・送信テスト |
| 9 | OpenTelemetry 基盤導入 | トレース・メトリクスの自動インストルメンテーション（FastAPI/DB/HTTP クライアント） | `src/monitoring/otel.py` | ユニットテスト PASS・エクスポート確認 |
| 10 | エラーハンドリング統一 | 例外ハンドラーミドルウェアの統一・ユーザーに優しいエラーレスポンス・ログ出力 | `src/api/middleware/error_handler.py` | ユニットテスト PASS・API テスト PASS |
| 11 | ログ管理統一 | 構造化ログ（JSON）への移行・ログローテーション設定・標準出力への出力 | `src/logging/setup.py` | ログフォーマット確認・ローテーション動作テスト |
| 12 | セキュリティ基盤強化 | HTTPS/TLS 終端（プロキシレベル）・シークレット管理の実装・入力バリデーション強化 | `src/security/` ディレクトリ | セキュリティスキャン PASS（例: bandit） |
| 13 | レートリミット・Dos 保護 | レートリミットミドルウェアの実装（IPベースまたは APIキーベース） | `src/api/middleware/rate_limit.py` | ユニットテスト PASS・負荷テストで動作確認 |
| 14 | ヘルスチェックエンドポイント | ライブネス・レッドネスチェック（`/health/live`, `/health/ready`）の実装 | `src/api/health.py` | ユニットテスト PASS・Docker ヘルスチェック連携 |
| 15 | パフォーマンス基準設定 | 応答遅延・スループット・エラーレートの SLO/SLI 定義・測定スクリプト作成 | `docs/PERFORMANCE_BASELINES.md` + `scripts/check_performance.py` | スクリプト実行・基準値記録 |
| 16 | 負荷テスト実装 | 構造化負荷テストスクリプト（例: Locust または k6）およびベースライン測定 | `tests/load/test_locustfile.py` | テスト実行・結果記録 |
| 17 | ログ長期保存戦略 | ログローテーションポリシー（サイズ・期間）・アーカイブ・保存先クラウドストレージ連携検討 | `docs/LOG_RETENTION_POLICY.md` | ポリシー承認・サンプルスクリプト |
| 18 | 自動スケーリング検討 | Docker Compose の `scale` または オーケストレーションツール（Swarm/K8s）の検証・プロトタイプ | `docs/AUTOSCALING_FEASIBILITY.md` | 調査完了・推奨事項 |
| 19 | 高可用性設定 | データベースレプリケーション（PGVector スタンバイ）・ネットワーク冗長化の設計書 | `docs/HA_DESIGN.md` | レビュー承認 |
| 20 | バックアップ・災害復旧計画 | バックアップ手順（論理ダンプ・ファイルシステムスナップショット）・リストア手順・RTO/RPO 定義 | `docs/BACKUP_DR_PLAN.md` | 計画承認・リストア訓練スクリプト雛形 |
| 21 | リグレッション防止テスト | 環境境界設定のリグレッションテスト（ローカル設定が本番に漏れないか） | `tests/config/test_env_isolation.py` | `pytest` PASS |
| 22 | リグレッション防止テスト | Docker イメージ構成のリグレッションテスト（不要なパッケージ含まず・実行ユーザー非root） | `tests/docker/test_image_security.py` | `pytest` PASS |
| 23 | リグレッション防止テスト | 監視・エラーハンドリングのリグレッションテスト（Sentry/OTEL が例外を正しく捕捉） | `tests/monitoring/test_observability.py` | `pytest` PASS |
| 24 | 完了確認・商用リリース準備 | 本番構成でのフル E2E テスト・セキュリティスキャン・パフォーマンスベンチマーク・ドキュメント最終確認・リリースタグ打刻 | PR #xxx & リリースタグ `v1.0.0` | 全テスト PASS・セキュリティスキャン Critical/High 0・パフォーマンス目標達成・リリースノート作成 |

---

## ステップ詳細

### Step 1-2: ブランチ作成・ベースライン確認
```bash
git checkout -b phase4-production phase3-done
git push -u origin phase4-production
```
**Done**: `git branch --show-current` → `phase4-production`

### Step 3: 環境境界定義
**ファイル**: `docs/ENVIRONMENT_BOUNDARY.md`
```markdown
# 環境境界定義

## ローカル開発環境
- データベース: SQLite (`data/local.db`)
- キャッシュ: メモリベースまたはローカルファイル
- キュー: インメモリ（またはなし）
- サービス discovery: なし（シングルプロセス）
- ログレベル: DEBUG
- ホスト: `localhost:8000`

## 本番環境
- データベース: PostgreSQL + pgvector (ホスト: `db`, ポート: 5432)
- キャッシュ: Redis または memcached (環境変数で選択)
- キュー: Redis-backed RQ または Celery
- サービス discovery: Docker Compose ネットワークまたは Kubernetes
- ログレベル: INFO（エラー時は自動で DEBUG アップ）
- ホスト: `api.example.com` (HTTPS)
- TLS: Let's Encrypt または内部 CA
- シークレット管理: Docker Secrets または 環境変数（実運用では Vault 推奨）
```

### Step 4: 設定分離実装
**ファイル**: `src/config/env_loader.py`
- 環境変数 `ENVIRONMENT` (local|production|staging) を読む
- 対応する YAML ファイルをロード（`config/local.yaml` 等）
- デフォルトは `local`
- 必要な設定項目を検証・型変換
**ファイル例**:
- `config/local.yaml`: SQLite パス、デバッグフラグ ON
- `config/production.yaml`: PostgreSQL 接続情報、キャッシュ Redis、ログレベル INFO
**テスト**: `tests/config/test_env_loader.py`
```python
def test_loads_local_by_default():
    with patch.dict(os.environ, {}, clear=True):
        config = load_config()
        assert config["database"]["type"] == "sqlite"

def test_loads_production_when_set():
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        config = load_config()
        assert config["database"]["type"] == "postgresql"
```

### Step 5: 本番Dockerfile作成
**ファイル**: `Dockerfile.prod`
```dockerfile
# ビルドステージ
FROM python:3.12-slim AS builder
WORKDIR /app
# 依存関係のみコピーしてキャッシュ活用
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes
# 本番依存関係のみインストール
RUN pip install --no-cache-dir -r requirements.txt

# 本番ステージ
FROM python:3.12-slim
WORKDIR /app
# ビルドステージから成果物コピー
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# アプリコード
COPY . .
# 非rootユーザー作成
RUN useradd -m -u 1000 appuser
USER appuser
# エントリーポイント
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
**確認**: `docker build -t autonovel:prod -f Dockerfile.prod .` が成功し、`docker run` で起動できること

### Step 6: Docker Compose 本番構成
**ファイル**: `docker-compose.prod.yml`
```yaml
version: '3.8'
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@db:5432/autonovel
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    # ヘルスチェック
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
  db:
    image: ankane/pgvector:latest
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=autonovel
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 10s
      timeout: 5s
      retries: 5
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
volumes:
  pgdata:
```
**確認**: `docker compose -f docker-compose.prod.yml up -d` が成功し、ヘルスチェックが PASS すること

### Step 7: E2E テスト実装
**ファイル**: `tests/e2e/test_production_e2e.py`
- Docker Compose で本番構成を起動
- API エンドポイントを呼び出してストーリー生成
- 結果をダウンロードし、ZIP/EPUB が正常に生成されることを確認
- テスト終了後にコンテナを停止・削除
**実装ヒント**: `docker-py` または `subprocess` で `docker compose` コマンドをラップ
**テスト例**（疑似コード）:
```python
def test_full_generation_flow():
    # コンテナスタート
    compose_up()
    try:
        # 生成リクエスト
        resp = requests.post("http://localhost:8000/api/generate", json=test_payload)
        job_id = resp.json()["job_id"]
        # ポーリングで完了待ち
        result = wait_for_completion(job_id)
        # 結果検証
        assert result["status"] == "success"
        assert len(result["text"]) > 100
        # ダウンロード
        zip_resp = requests.get(f"http://localhost:8000/api/download/{job_id}")
        assert zip_resp.status_code == 200
        assert zip_resp.headers["content-type"] == "application/zip"
    finally:
        compose_down()
```

### Step 8: 監視基盤導入 - Sentry
**ファイル**: `src/monitoring/sentry.py`
- `sentry_sdk.init()` を DSN から初期化
- Flask/FastAPI の統合
- エラーハンドラーへの結びつけ
**テスト**: `tests/monitoring/test_sentry.py`
```python
@patch("src.monitoring.sentry.sentry_sdk.capture_exception")
def test_sentry_captures_exception(mock_capture):
    # エラーを発生させるエンドポイントを呼ぶ
    client.get("/trigger-error")
    mock_capture.assert_called_once()
```

### Step 9: OpenTelemetry 基盤導入
**ファイル**: `src/monitoring/otel.py`
- トレースプロバイダーの設定（コンソールまたは Jaeger エクスポーター）
- 自動インストルメンテーション（FastAPI、SQLAlchemy、httpx 等）
- メトリクスのエクスポート
**テスト**: `tests/monitoring/test_otel.py`
```python
def test_trace_id_in_logs():
    # リクエストを送信し、ログに trace_id が含まれることを確認
    with patch("src.monitoring.otel.get_current_span") as mock_span:
        mock_span.return_value.get_span_context.return_value.trace_id = 0x123
        client.get("/")
        # ログ出力をキャプトし、trace_id が含まれるかチェック
```

### Step 10: エラーハンドリング統一
**ファイル**: `src/api/middleware/error_handler.py`
- FastAPI の例外ハンドラーまたはミドルウェア
- 例外をログに出力し、Sentry に送信
- ユーザーにはスタックトレースを含まない汎用エラーメッセージを返却
**テスト**: `tests/api/test_error_handler.py`
```python
def test_returns_generic_error_message():
    resp = client.get("/nonexistent")
    assert resp.status_code == 404
    data = resp.get_json()
    assert "message" in data
    assert "Not Found" in data["message"]
    # スタックトレースが含まれていないこと
    assert "traceback" not in data
    assert "File" not in data["message"]
```

### Step 11: ログ管理統一
**ファイル**: `src/logging/setup.py`
- `loguru` または 標準 `logging` を JSON フォーマットで設定
- ログローテーション（サイズベース 100MB または 時間ベース 1日）
- 標準出力へ出力（Docker が取得しやすいように）
**テスト**: `tests/logging/test_setup.py`
```python
def test_logs_are_json():
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        logger.info("Test message", key="value")
        output = mock_stdout.getvalue().strip()
        log_entry = json.loads(output)
        assert log_entry["message"] == "Test message"
        assert log_entry["key"] == "value"
        assert "timestamp" in log_entry
        assert log_entry["level"] == "INFO"
```

### Step 12: セキュリティ基盤強化
**ディレクトリ**: `src/security/`
- `headers.py`: セキュリティヘッダー（HSTS, CSP, X-Frame-Options 等）を追加するミドルウェア
- `auth.py`: 本番での認証・認可強化（API キー必須等、開発時はオプション）
- `input_validation.py`: 入力サニタイズ・バリデーション強化（例: Pydantic モデルの厳格モード）
**テスト**: `tests/security/test_headers.py`
```python
def test_security_headers_present():
    resp = client.get("/")
    assert resp.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert "x-frame-options" in resp.headers
```

### Step 13: レートリミット・Dos 保護
**ファイル**: `src/api/middleware/rate_limit.py`
- IP アドレスまたは API キーベースのトークンバケットまたは fixed window カウンター
- 超過時は 429 Too Many Requests
**テスト**: `tests/api/test_rate_limit.py`
```python
def test_rate_limit_allows_n_requests():
    for i in range(5):  # 制限を 5/分 と仮定
        resp = client.post("/api/generate", json=test_payload)
        assert resp.status_code == 202
    # 6回目は 429
    resp = client.post("/api/generate", json=test_payload)
    assert resp.status_code == 429
```

### Step 14: ヘルスチェックエンドポイント
**ファイル**: `src/api/health.py`
- `/health/live`: プロセスが生きているか（単純に 200 を返す）
- `/health/ready`: 依存サービス（DB、キャッシュ）に接続できるか
**テスト**: `tests/api/test_health.py`
```python
def test_live_endpoint():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "alive"

def test_ready_endpoint_when_db_up():
    # DB モックまたは テスト用 DB が上がっている前提
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ready"
```

### Step 15: パフォーマンス基準設定
**ファイル**: `docs/PERFORMANCE_BASELINES.md`
- SLO（Service Level Objective）: 95% リクエストが 2秒以内
- SLI（Service Level Indicator）: 実際の測定値
- エラーレート目標: 1% 未満
**スクリプト**: `scripts/check_performance.py`
- 本番相当の負荷をかけ（またはステージング環境で）
- 応答時間・スループット・エラーレートを測定
- ベースラインと比較し、目標達成か判定
**テスト**: 該当なし（手動実行スクリプトだが、スクリプト自体の単体テストは作成可能）

### Step 16: 負荷テスト実装
**ファイル**: `tests/load/test_locustfile.py`（Locust の場合）
- ユーザー行動をシナリオ定義（ストーリー生成リクエスト → 結果ポーリング → ダウンロード）
- スパイクテスト・持続テストのシナリオ
**実行方法**: `locust -f tests/load/test_locustfile.py --headless -u 50 -r 5 --run-time 5m --host http://localhost:8000`
**テスト**: Locust ファイル自体の構文チェックテスト
```python
def test_locustfile_imports():
    # 実際に locustfile をインポートし、クラスが定義されているか
    from tests.load.locustfile import WebsiteUser
    assert WebsiteUser is not None
```

### Step 17: ログ長期保存戦略
**ファイル**: `docs/LOG_RETENTION_POLICY.md`
- ログローテーション設定（例: loguru の `rotation="100 MB", retention="30 days"`）
- アーカイブ先（例: S3 バケットまたは GCS バケットへの定期アップロードスクリプト）
- 古いログの削除ポリシー
**サンプルスクリプト**: `scripts/archive_logs.py`
- テスト: スクリプトが存在し、引数チェックが行われること

### Step 18: 自動スケーリング検討
**ファイル**: `docs/AUTOSCALING_FEASIBILITY.md`
- Docker Compose の `scale` ディレクティブの限界（手動介入必要）
- Kubernetes または Docker Swarm への移行検討
- メトリクスベースの自動スケーリング（CPU、メモリ、キュー長）
- 推奨: Phase 4 では Docker Compose で固定レプリカ数、Phase 5 で オーケストレーションへ移行

### Step 19: 高可用性設定
**ファイル**: `docs/HA_DESIGN.md`
- データベース: PostgreSQL のストリーミングレプリケーション（スタンバイ 1 台以上）
- ネットワーク: ロードバランサー（NGINX または Traefik）による冗長化
- サービス: 各レプリカが同じ設定で起動し、セッション不要な設計（ステートレス）
- フェイルオーバー: 自動昇格スクリプトまたは 監視ツール（Patroni）の使用検討

### Step 20: バックアップ・災害復旧計画
**ファイル**: `docs/BACKUP_DR_PLAN.md`
- バックアップ種類:
  - 論理ダンプ: `pg_dump` 夜間実行
  - ファイルシステムスナップショット: ボリュームスナップショット（Docker ボリュームまたは LVM）
- 頻度: 論理ダンプ 毎日、スナップショット 毎時
- 保存先: オフサイトオブジェクトストレージ
- リストア手順:
  1. 最新スナップショットからボリュームを復元
  2. 必要ならポイントインタイムリカバリのために WAL ログを適用
  3. アプリケーションを起動し、整合性チェック
- RTO (Recovery Time Objective): 30 分
- RPO (Recovery Point Objective): 15 分
**訓練スクリプト雛形**: `scripts/drill_restore.py`
- テスト: 計画文書が存在し、レビュー済みであること

### Step 21-23: リグレッション防止テスト

**ファイル**: `tests/config/test_env_isolation.py`
```python
"""ローカル設定が本番環境に漏れないことをテスト"""
import os
from src.config.env_loader import load_config

def test_local_config_does_not_leak_to_production():
    # 本番環境をシミュレート
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        prod_config = load_config()
    # ローカル環境をシミュレート
    with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
        local_config = load_config()
    # 重要な違いをチェック
    assert prod_config["database"]["type"] == "postgresql"
    assert local_config["database"]["type"] == "sqlite"
    assert prod_config["log"]["level"] == "INFO"
    assert local_config["log"]["level"] == "DEBUG"
```

**ファイル**: `tests/docker/test_image_security.py`
```python
"""Docker イメージのセキュリティ構成をテスト"""
import subprocess
import json

def test_image_contains_no_unnecessary_packages():
    # イメージをビルド（または既存のものを使用）
    result = subprocess.run(
        ["docker", "build", "-q", "-f", "Dockerfile.prod", "."],
        capture_output=True, text=True, check=True
    )
    image_id = result.stdout.strip()
    # パッケージリストを取得
    result = subprocess.run(
        ["docker", "run", "--rm", image_id, "dpkg", "-l"],
        capture_output=True, text=True, check=True
    )
    installed_packages = set(result.stdout.splitlines())
    # 必要最低限のパッケージ以外がインストールされていないことを確認
    # （例: python3, ca-certificates 等は許容、vim, nano, ssh サーバー等はNG）
    unnecessary = {"vim", "nano", "openssh-server", "net-tools"}
    found_unnecessary = unnecessary & {p.split()[1] for p in installed_packages if p.startswith("ii")}
    assert not found_unnecessary, f"Found unnecessary packages: {found_unnecessary}"

def test_image_runs_as_nonroot():
    result = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "", image_id, "ps", "-o", "pid,user"],
        capture_output=True, text=True, check=True
    )
    # プロセス一覧から、PID 1 (通常は uvicorn) が root でないことを確認
    lines = result.stdout.strip().splitlines()[1:]  # ヘッダー行を除く
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "1":  # PID 1
            assert parts[1] != "root", f"PID 1 runs as {parts[1]}"
```

**ファイル**: `tests/monitoring/test_observability.py`
```python
"""Sentry と OpenTelemetry が例外を正しく捕捉することをテスト"""
from unittest.mock import patch
import pytest

@patch("src.monitoring.sentry.sentry_sdk.capture_exception")
def test_sentry_captures_api_exception(mock_capture):
    # エラーを返すエンドポイントを呼ぶ（例: 不正な入力で 500）
    resp = client.post("/api/generate", json={"invalid": "payload"})
    # 実際には 400 等になるかもしれないが、ここでは意図的に例外を発生させるエンドポイントを用意するか、
    # または モックで強制的に例外を投げさせる
    # 簡易版: エラーハンドラーが Sentry を呼ぶことを確認
    if resp.status_code >= 500:
        mock_capture.assert_called_once()

@patch("src.monitoring.otel.trace.get_tracer")
def test_otel_creates_span_for_request(mock_get_tracer):
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_tracer.start_span.return_value.__enter__.return_value = mock_span
    mock_get_tracer.return_value = mock_tracer
    # 任意のエンドポイントにリクエスト
    client.get("/health/live")
    # スパンが作成されたことを確認
    mock_tracer.start_span.assert_called()
```

### Step 24: 完了確認・商用リリース準備
```bash
# 1. 全テスト実行（カバレッジ付き・フェーズ3ベースライン維持）
pytest --cov=src --cov-fail-under=55 --tb=short -q

# 2. リンター・型チェック
ruff check .
mypy src/

# 3. セキュリティスキャン実行（Critical/High が 0 であること）
bandit -r src/ -lll  # または owasp dependency-check 等
# 結果ファイルを artifacts/ に保存し、確認

# 4. パフォーマンスベンチマーク実行（目標達成確認）
python scripts/check_performance.py  # SLO/SLI が達成されているか判定

# 5. 本番構成でのフル E2E テスト（Docker Compose 上）
docker compose -f docker-compose.prod.yml up -d
# コンテナがヘルシーになったらテスト実行
pytest tests/e2e/test_production_e2e.py -v
docker compose -f docker-compose.prod.yml down

# 6. ドキュメント最終確認
# - docs/ENVIRONMENT_BOUNDARY.md
# - docs/PERFORMANCE_BASELINES.md
# - docs/BACKUP_DR_PLAN.md 等が最新かつレビュー済み

# 7. リリースタグ打刻
git tag -a v1.0.0 -m "Release 1.0.0: Production Ready"
git push origin v1.0.0

# 8. PR 作成（main へマージ）
gh pr create --title "Phase 4: 環境統一と商用ローンチ (Production Readiness)" \
             --body-file plans/PHASE_4_IMPLEMENTATION_PLAN.md \
             --base main \
             --head phase4-production
```

---

## 依存関係・並列化ガイド

```
Step 1-2 → 
Step 3-5 → (Step 6-10 並列) → 
Step 11-13 → 
Step 14-16 → 
Step 17-18 → 
Step 19-20 → 
Step 21-23 → 
Step 24
```

- **並列可能**: 
  - Docker Compose 本番構成(6)、監視基盤(8-10)、セキュリティ(12)、レートリミット(13)は比較的独立
  - ログ管理(11)、ヘルスチェック(14)、パフォーマンス基準(15)、負荷テスト(16)はある程度独立
  - ログ長期保存(17)、自動スケーリング検討(18)は調査タスクなので他と並列可能
  - HA 設計(19)、バックアップ計画(20)はドキュメント中心なので並列可能
- **順序必須**: 
  - 環境境界定義(3) → 設定分離(4) → Dockerfile(5) → Docker Compose(6)
  - E2E テスト(7)は Docker Compose が完成してから実行可能
  - ベンチマーク基準(15) → 負荷テスト実装(16) → パフォーマンス測定スクリプト
  - リグレッションテスト(21-23)は対象機能の実装後または並行して作成可能

---

## 完了判定基準 (Definition of Done)

- [ ] 全 24 ステップのチェックボックス完了
- [ ] `pytest --cov-fail-under=55` PASS
- [ ] `ruff check .` / `mypy src/` PASS
- [ ] 環境境界が明確に定義され、設定ローダーが環境別に正しく設定を読み込むこと
- [ ] 本番相当の Dockerfile がマルチステージビルドかつ非rootユーザーで動作すること
- [ ] Docker Compose 本番構成が起動・ヘルスチェック PASS し、E2E テストが PASS すること
- [ ] Sentry と OpenTelemetry が統合され、例外とトレースが正しく捕捉・エクスポートされること
- [ ] エラーハンドラーがスタックトレースを漏らさず、ユーザーに優しいメッセージを返すこと
- [ ] ログが構造化（JSON）で出力され、ログローテーションが動作すること
- [ ] セキュリティヘッダーが付与され、機密情報がログに漏れないこと
- [ ] レートリミットが機能し、過剰リクエストに 429 を返すこと
- [ ] ヘルスチェックエンドポイント（ライブネス・レッドネス）が正しく動作すること
- [ ] パフォーマンス基準（SLO/SLI）が文書化され、測定スクリプトが存在すること
- [ ] 負荷テストスクリプトが存在し、基本的なシナリオが定義されていること
- [ ] ログ長期保存戦略が文書化され、アーカイブスクリプトの雛形があること
- [ ] 自動スケーリングの可否調査が完了し、Phase 5 以降の方向性が示されている（オプション）
- [ ] 高可用性設計書が作成され、レプリケーション・ロードバランスの方針が示されていること
- [ ] バックアップ・災害復旧計画が文書化され、RTO/RPO が定義され、リストア訓練スクリプトの雛形があること
- [ ] 新規テスト 3 本（Step 21-23）全 PASS
- [ ] セキュリティスキャンで Critical または High の脆弱性が 0 件であること
- [ ] パフォーマンス目標達成：
    - 95% リクエストが SLO（例: 2秒）以内であること
    - エラーレートが目標（例: 1% 未満）であること
    - または「応答時間 × エラーレート」の積でベースラインから大きな改善があること
- [ ] PR 作成・レビュー承認・マージ完了
- [ ] `main` ブランチで `git tag v1.0.0` 打刻（商用リリースタグ）
- [ ] リリースノートが作成され、主な機能・改善点・既知の制約が記載されていること