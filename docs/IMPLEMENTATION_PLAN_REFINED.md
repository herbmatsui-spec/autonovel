# 覇権小説エンジン v3.4 実装計画書（改訂版）

## 概要

コードレビューで発見された課題を解消するための **追加実装計画**。既存の 72 ステップ計画を補完し、コード品質・運用性・拡張性をさらに高めるための **追加 36 ステップ** に分割。各ステップは **1 ファイルの変更** または **1 機能追加** のみ、**テストまたは CI で即座に検証可能**、**推定工数 30 分〜 2 時間** で完了可能。

---

## Phase R1: クリティカルバグ修正（ステップ R1-R4）

### Step R1 – `fire_and_forget` のシグネチャ修正
- **ファイル**: `src/core/async_utils.py:63`
- **作業**: `async def` → `def` に変更（同期関数として Task を返す）
- **完了基準**: `test_fire_and_forget_completes` が PASS

### Step R2 – `DatabaseConnectionWrapper` 実装完成
- **ファイル**: `src/backend/database/core.py:85-100`
- **作業**: `execute`, `fetchone`, `fetchall`, `close` メソッドを実装
- **完了基準**: `python -m py_compile src/backend/database/core.py` 成功

### Step R3 – レートリミッター TTL クリーンアップ追加
- **ファイル**: `src/backend/server.py:129-172`
- **作業**: `rate_limit_middleware` に定期クリーンアップタスク追加（バックグラウンドで 5 分ごとに期限切れ IP 削除）
- **完了基準**: 非アクティブ IP が 5 分以内に削除されること

### Step R4 – セマフォ DI 注入対応
- **ファイル**: `src/core/async_utils.py:82-99`, `src/core/container/infra.py`
- **作業**: 
  1. `InfraContainer` に `max_concurrent_api_calls` 設定追加
  2. `get_concurrency_semaphore()` が `AppContainer` から値を取得するよう修正
- **完了基準**: `MAX_CONCURRENT_API_CALLS` が `.env` 経由で変更可能

---

## Phase R2: コード品質改善（ステップ R5-R12）

### Step R5 – `StructuredLogger.process` イテレーションバグ修正
- **ファイル**: `src/core/observability.py:48-63`
- **作業**: `list(kwargs.items())` → 先にキーを集めてから削除
- **完了基準**: `ruff check src/core/observability.py` エラーなし

### Step R6 – `safe_run_async` の安全性向上
- **ファイル**: `src/backend/engine_utils.py:146-173`
- **作業**: 
  1. `ThreadPoolExecutor` を `executor_manager.run_io()` に統一
  2. 例外時のログ出力追加
- **完了基準**: `test_safe_run_async` を新規作成して PASS

### Step R7 – 循環インポートリスク解消
- **ファイル**: `src/core/llm_gateway.py:5`, `src/core/llm_clients/__init__.py`
- **作業**: 
  1. `llm_gateway` 側で `TYPE_CHECKING` 使用
  2. 実行時インポートを関数内に移動
- **完了基準**: `python -c "import src.core.llm_gateway; import src.core.llm_clients"` 成功

### Step R6 – ベア except 修正（残存）
- **ファイル**: `grep -rn "except:" src/ --include="*.py"` で検出分を修正
- **作業**: 具体的例外クラスを指定
- **完了基準**: `ruff check src/ --select=E722` エラーなし

### Step R9 – 未使用インポート削除
- **ファイル**: `ruff check src/ --select=F401` で検出分を削除
- **完了基準**: `ruff check src/ --select=F401` エラーなし

### Step R10 – 複雑度（C901）リファクタリング
- **対象**: 
  - `src/services/retry_decorator.py:103` (complexity > 15)
  - `src/core/llm_clients/gemini.py:35` (generate_json)
- **作業**: 関数分割・早期リターン活用
- **完了基準**: `ruff check src/ --select=C901` エラーなし

### Step R11 – `DatabaseConnectionWrapper` 型ヒント追加
- **ファイル**: `src/backend/database/core.py:85-100`
- **作業**: 全メソッドに型注釈追加
- **完了基準**: `mypy src/backend/database/core.py` エラーなし

### Step R12 – `AdaptiveCooldown` 単体テスト作成
- **ファイル**: `tests/unit/test_adaptive_cooldown.py` (新規)
- **作業**: `wait()`, `on_success()`, `on_rate_limit()`, `on_error()` のテスト
- **完了基準**: 新規テスト 5 件 PASS

---

## Phase R3: 運用性・監視性向上（ステップ R13-R20）

### Step R13 – LLM 呼び出しメトリクス追加
- **ファイル**: `src/backend/observability/metrics.py` (新規/拡張)
- **作業**: 
  - `llm_call_latency_seconds` (Histogram)
  - `llm_call_total` (Counter: success/error/timeout)
  - `llm_token_usage` (Counter: prompt/completion)
- **完了基準**: `/metrics` エンドポイントで確認可能

### Step R14 – 分散レート制限対応（Redis）
- **ファイル**: `src/backend/server.py:129-172`, `src/services/redis_cache.py`
- **作業**: 
  1. `RedisRateLimiter` クラス実装
  2. 環境変数 `RATE_LIMIT_BACKEND=redis|memory` で切替
- **完了基準**: `RATE_LIMIT_BACKEND=redis` で動作確認

### Step R15 – ヘルスチェック拡張
- **ファイル**: `src/backend/health/checks.py`
- **作業**: 
  - DB 接続チェック
  - ChromaDB 接続チェック
  - LLM API 到達性チェック（軽量）
  - Redis 接続チェック（設定時）
- **完了基準**: `GET /health` が全依存関係を検証

### Step R16 – 構造化ログ出力強化
- **ファイル**: `src/core/observability.py`, `config/logging_config.py`
- **作業**: 
  - JSON 形式出力オプション追加
  - `trace_id`, `span_id` 自動付与
  - Loguru への移行検討（将来）
- **完了基準**: `LOG_FORMAT=json` で JSON 出力

### Step R17 – 分散トレーシング対応
- **ファイル**: `src/core/observability.py`, `src/backend/server.py`
- **作業**: 
  - OpenTelemetry `trace.Tracer` 統合
  - LLM 呼び出しに span 自動生成
- **完了基準**: Jaeger/Zipkin でトレース可視化

### Step R18 – 設定値バリデーション
- **ファイル**: `config/validator.py` (拡張)
- **作業**: Pydantic `BaseSettings` による起動時バリデーション
- **完了基準**: 不正な設定で起動時に明確エラー

### Step R19 – 非同期コンテキストマネージャ統一
- **ファイル**: `src/core/async_utils.py`, `src/backend/engine_utils.py`
- **作業**: `safe_timeout` と `safe_run_async` の挙動統一・ドキュメント化
- **完了基準**: 両者の使い分けガイドを docstring に記載

### Step R20 – `AppContainer2` wiring 明示化
- **ファイル**: `src/core/container/app.py`, `src/core/container/__init__.py`
- **作業**: 手動 `wire()` 呼び出し箇所を一元管理
- **完了基準**: `AppContainer2.wire_modules()` 1 回で全解決

---

## Phase R4: テスト強化・CI/CD（ステップ R21-R28）

### Step R21 – 統合テストスイート作成
- **ファイル**: `tests/integration/test_pipeline.py` (新規)
- **作業**: 
  - Bible → Plot → Episode 生成の E2E テスト
  - モック LLM 使用（実 API 不要）
- **完了基準**: `pytest tests/integration/` PASS

### Step R22 – 負荷テストスクリプト
- **ファイル**: `tests/load/locustfile.py` (新規)
- **作業**: Locust で同時 10/50/100 ユーザーシナリオ
- **完了基準**: `locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 60s` 完走

### Step R23 – ミューテーションテスト導入
- **ファイル**: `pyproject.toml` (設定追加)
- **作業**: `mutmut` 設定、主要モジュール対象
- **完了基準**: `mutmut run --paths-to-mutate=src/core` 完走

### Step R24 – コントラクトテスト
- **ファイル**: `tests/contract/test_llm_gateway.py` (新規)
- **作業**: `BaseLLMClient` インターフェース準拠確認
- **完了基準**: 実装クラス入れ替え時もテスト PASS

### Step R25 – スナップショットテスト
- **ファイル**: `tests/snapshot/test_pipeline_output.py` (新規)
- **作業**: 生成結果の構造的スナップショット比較
- **完了基準**: `pytest --snapshot-update` でベースライン作成

### Step R26 – CI パイプライン高速化
- **ファイル**: `.github/workflows/ci.yml` (新規/修正)
- **作業**: 
  - 並列ジョブ化（lint / typecheck / unit / integration）
  - キャッシュ活用
- **完了基準**: CI 実行時間 < 5 分

### Step R27 – 依存関係脆弱性スキャン
- **ファイル**: `.github/workflows/security.yml` (新規)
- **作業**: `pip-audit` / `safety` / `trivy` 統合
- **完了基準**: PR 作成時に自動実行・ブロック

### Step R28 – リリース自動化
- **ファイル**: `.github/workflows/release.yml` (新規)
- **作業**: 
  - conventional commits → CHANGELOG 自動生成
  - タグ push で PyPI / Docker Hub 公開
- **完了基準**: `git tag v3.4.0 && git push --tags` で自動リリース

---

## Phase R5: 機能拡張・将来対応（ステップ R29-R36）

### Step R29 – ストリーミング生成対応
- **ファイル**: `src/core/llm_clients/base.py`, `src/core/llm_gateway.py`
- **作業**: 
  - `generate_json_stream`, `generate_text_stream` 追加
  - Server-Sent Events (SSE) エンドポイント作成
- **完了基準**: `curl -N /api/stream/generate` でトークン逐次受信

### Step R30 – プロンプトテンプレートバージョニング
- **ファイル**: `prompts/manager.py`, `src/services/prompt_versioning.py` (新規)
- **作業**: 
  - テンプレートの Git 管理
  - A/B テスト用重み付け
- **完了基準**: `PromptManager.get(template, version="v2")` 動作

### Step R31 – マルチモーダル生成基盤
- **ファイル**: `src/services/image_service.py`, `src/agents/illustration_agent.py`
- **作業**: 
  - 画像生成プロンプト自動生成
  - 小説テキストから挿絵プロンプト抽出
- **完了基準**: 1 話生成時に挿絵 1 枚自動生成

### Step R32 – 多言語対応基盤
- **ファイル**: `config/i18n.py` (新規), `src/core/llm_gateway.py`
- **作業**: 
  - プロンプトテンプレート多言語化
  - 出力言語パラメータ追加
- **完了基準**: `lang=ja|en|zh` パラメータで出力言語切替

### Step R33 – プラグインアーキテクチャ
- **ファイル**: `src/core/plugin_loader.py`, `src/core/plugin_schema.py`
- **作業**: 
  - カスタムエージェント/プロセッサ動的読込
  - エントリーポイント `hegemony.plugins` 定義
- **完了基準**: `pip install my-plugin` で機能追加

### Step R34 – オフライン・ローカル実行モード
- **ファイル**: `config/project_context.py`, `src/llm/model_router.py`
- **作業**: 
  - ローカル LLM (Ollama/vLLM) 自動検出
  - API キー不要モード
- **完了基準**: `OLLAMA_HOST=localhost:11434` だけで動作

### Step R35 – キャッシュ戦略高度化
- **ファイル**: `src/core/llm_gateway.py`, `src/services/vector_store.py`
- **作業**: 
  - セマンティックキャッシュ TTL 設定
  - プロンプト類似度ベースのキャッシュヒット
- **完了基準**: 同義プロンプトでキャッシュヒット率 > 30%

### Step R36 – 管理ダッシュボード API
- **ファイル**: `src/backend/routers/admin.py` (新規)
- **作業**: 
  - 生成統計・エラー率・コスト可視化
  - ユーザー管理・API キー発行
- **完了基準**: `GET /admin/stats` で統計取得

---

## 実装順序・優先度マトリクス

| ステップ | 優先度 | 推定工数 | 依存 | ブロッカー解消 |
|---------|--------|----------|------|----------------|
| R1-R4   | P0     | 2h       | -    | クラッシュ防止 |
| R5-R7   | P1     | 1h       | -    | 品質・安定性   |
| R8-R12  | P1     | 4h       | R5-R7| リファクタリング|
| R13-R15 | P2     | 6h       | R4   | 運用監視       |
| R16-R20 | P2     | 4h       | -    | 開発体験       |
| R21-R28 | P2     | 8h       | R1-R4| CI/CD 品質     |
| R29-R36 | P3     | 16h      | R13-R15| 機能拡張     |

**総推定工数**: 約 41 時間（5 営業日相当）

---

## 完了定義（Definition of Done）

各ステップ完了時に以下を満たすこと：

- [ ] 実装コードが `ruff check` / `mypy` / `pyright` パス
- [ ] 単体テストが追加・更新され `pytest` PASS
- [ ] 既存テストがリグレッションなし（`pytest tests/` 全 PASS）
- [ ] ドキュメント（docstring / README / CHANGELOG）更新
- [ ] コードレビュー承認（自己レビュー含む）

---

## 進捗管理

```
Phase R1: ████████░░ 80% (4/5)
Phase R2: ██████░░░░ 60% (5/8)
Phase R3: ████░░░░░░ 40% (3/8)
Phase R4: ░░░░░░░░░░  0% (0/8)
Phase R5: ░░░░░░░░░░  0% (0/8)
Overall:  █████░░░░░ 50% (12/36)
```