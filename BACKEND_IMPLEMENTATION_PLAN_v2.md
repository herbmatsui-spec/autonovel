# バックエンド 詳細実装計画書 v2.0

## 概要

本書は「バックエンド評価レポート」(2026-08-29) および既存 `IMPLEMENTATION_PLAN.md` / `IMPLEMENTATION_PLAN_DETAIL.md` で挙げられた全課題に対する、段階的かつ検証可能な実装計画を定義する。
対象は `src/backend/`, `src/core/container/`, `src/api/` を中心とするサーバサイド全体。

### 評価サマリ(再掲)

- **良い点**: レイヤ分離、UoW + Outbox、SSE の三段フォールバック、SSRF/HSTS/CORS、型・lint・テストツール整備
- **課題**: 神エンジン残置、設定のグローバル mutable 化、TODO 残し、ヘルスチェック過剰、テスト偏在、Facade 肥大

### スコープ

- ✅ 含める: セキュリティ/並行性/トランザクション/SSE/Huey/エンジン分割/DI 整理/テスト拡充
- ❌ 含めない: フロントエンド (`frontend/`)、LLM プロンプト品質、プロット生成のアルゴリズム改良

### 完了定義 (Definition of Done)

1. Critical/High 項目が全て修正され、CI が green
2. 既存テストが全件パス(回帰なし)
3. 新規追加テストのカバレッジ: 該当モジュール +20pt 以上
4. mypy strict / ruff / pre-commit 全て clean
5. `/docs` (OpenAPI) のバージョンが `pyproject.toml` と一致
6. ベンチマーク(後述)でレイテンシ劣化なし

---

## 対応優先順位の全体マップ

| 優先度 | 件数 | 工数合計 | フェーズ |
|--------|------|----------|----------|
| Critical | 4 | 5.0h | P1 |
| High | 8 | 16.0h | P2 |
| Medium | 12 | 18.5h | P3 |
| Low | 9 | 7.0h | P4 |
| **合計** | **33** | **46.5h** | 約 6 営業日 |

---

## Critical (P1: 即時対応)

### C1: `_apply_config_overrides` の二重呼び出しと競合

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/tasks.py:56-88, 162-199` |
| 問題 | (1) 162行目で `_apply_config_overrides(config_dict)` を呼んだ直後、165行目で再度呼び出し(戻り値破棄)。(2) グローバル `Settings` を `setattr` で書き換えるため、Huey タスクの並行実行で他タスクの設定が上書きされる。 |
| 影響 | (1) `finally` 節で「存在しない original_value」を `delattr` しようとして `AttributeError`、(2) ユーザ A の API キーがユーザ B のタスク実行中に漏洩するリスク |
| 修正方針 | 1. 二重呼び出しを削除(`overrides` 変数のみ使用)。<br>2. 設定オーバーライドを `contextvars.ContextVar` ベースに移行。<br>3. `get_settings()` を ContextVar から読むよう `config/settings.py` をラップ。<br>4. `finally` 節は ContextVar リセットに置換。 |
| 検証 | (a) 2 タスク並列実行で `Settings.gemini_api_key` が混ざらないこと、(b) 例外発生時に ContextVar が必ずリセットされるユニットテスト |
| 工数 | 1.5h |
| 依存 | `config/settings.py` の ContextVar 化 |

### C2: CORS 設定の起動時検証強化

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/server.py:216-230`, `config/cors_config.py` |
| 問題 | 検証ロジックは存在するが、`raise ValueError` がアプリ起動を即死させ、起動ログからの原因追跡が困難 |
| 修正方針 | (1) 起動時バリデーションを `lifespan` に移動し、`logging.error` で詳細出力後 `RuntimeError` を再送出。<br>(2) `cors_config.py` のデフォルトを `[]` にして未設定を許容(本番では `ALLOWED_ORIGINS` 環境変数必須を `README` に明記)。<br>(3) `--strict-cors` フラグ導入で開発時のサイレント失敗を防ぐ。 |
| 検証 | 異常設定で起動失敗すること、正常設定で起動成功することの統合テスト |
| 工数 | 1.0h |
| 依存 | なし |

### C3: API キー `test*` フォールバックの削除(本番強制)

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/auth.py:62-73, 99-108` |
| 問題 | `ENVIRONMENT != "production"` で `test` プレフィックスのキーが認証通過する。本番誤設定時に `AUTH_DISABLED` だけで守られている。 |
| 修正方針 | 1. `test*` フォールバックを削除し、未設定時は常に拒否。<br>2. 開発用には `ALLOWED_API_KEYS` の明示設定を強制し、未設定なら起動時に `RuntimeError`(`get_api_key_service`)。<br>3. 開発時のみ特例を許可する `AUTH_DEV_BYPASS=1` 環境変数を追加(本番では無視)。 |
| 検証 | (a) `test_xxx` で 403 になること、(b) `AUTH_DEV_BYPASS=1` + `ENVIRONMENT=development` でのみバイパス可、(c) `ENVIRONMENT=production` でのバイパス不可 |
| 工数 | 0.5h |
| 依存 | なし |

### C4: ヘルスチェックの LLM 実呼び出しデフォルト無効化

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/health/checks.py:121-155` |
| 問題 | `/health` ごとに LLM へ実リクエストが飛ぶ。K8s livenessProbe が 10s 間隔で叩くと API 課金が爆発し、LLM 側レート制限で Probe が赤くなり無意味な再起動を誘発する。 |
| 修正方針 | 1. `check_llm_gateway` のデフォルトを `HealthStatus.OK` 返却 + `details="llm_check_disabled_default"` に変更。<br>2. 有効化は `KAKU_HEALTH_CHECK_LLM=true` の明示オプトインのみ。<br>3. `/health/live` (LLM 無し) と `/health/ready` (全項目) を分離。 |
| 検証 | デフォルトで LLM 呼出ゼロ、ネット切断状態で 200、`KAKU_HEALTH_CHECK_LLM=true` 時のみ実呼出 |
| 工数 | 2.0h |
| 依存 | ルータ分割 |

---

## High (P2: 1週間以内)

### H1: `engine_facade` の肥大化解消

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/engine_facade.py:42-128` |
| 問題 | 20 個の `@property` が engine の属性を素通しするだけの構造で、ファサード自身が神クラスを再生産。内部実装が漏れ、ADR-0004 の段階的分割が道半ば。 |
| 修正方針 | 1. `EngineFacade` から `_engine` の個別プロパティを全削除し、`engine_impl` アクセッサ 1 個のみ残す。<br>2. 利用側を `engine_facade.engine_impl.repo` のように 1 段深くする(段階的移行)。<br>3. `protocols.py` で必要なメソッドだけを `EngineFacadeProtocol` として定義し、IDE 補完を保持。<br>4. 旧プロパティは `DeprecationWarning` を 1 リリース出し、次版で削除。 |
| 検証 | 既存テストがパス、`grep -r 'engine_facade\.' src/ | grep -v engine_impl` がエラーとなる呼び出しゼロ |
| 工数 | 3.0h |
| 依存 | なし(影響範囲が広い場合は H2 と同時) |

### H2: `UltimateHegemonyEngine` の段階的分解(コア分離)

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/engine.py:43-304` |
| 問題 | 42 引数のコンストラクタ、内部に 14 個のドメイン依存を保持。テスト時のモック作成が困難。 |
| 修正方針 | 1. `EngineDeps`(既に存在) を Pydantic モデル化してイミュータブル化。<br>2. `UltimateHegemonyEngine` を「薄いオーケストレータ(委譲のみ)」と「実装を持つ engine_*.py 群」に分割。<br>3. 各 `engine_*.py` を `Protocol` ベースでテスト可能に(`src/core/interfaces.py` への登録)。<br>4. 既存呼び出し側は `EngineFacade.engine_impl.method()` 形式のまま動作。 |
| 検証 | (a) `EngineDeps` 単体テスト、(b) `UltimateHegemonyEngine` の引数 ≤ 5、(c) 全ワークフローテスト緑 |
| 工数 | 4.0h |
| 依存 | H1 |

### H3: レートリミッタのアトミック化 (Lua スクリプト)

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/rate_limit.py:21-41` |
| 問題 | 既に対応済みの Lua 版 `_RATE_LIMIT_LUA_SCRIPT` は存在するが、デフォルトで fail_close。Redis 障害時に 503 が返りサービス全停止。 |
| 修正方針 | 1. フェイルオープン/クローズを `RATE_LIMIT_FAIL_OPEN` 環境変数で制御(現状は定数固定)。<br>2. 障害発生時のフォールバックとして、ローカル token bucket (in-memory, per-process) を併用。<br>3. 503 ではなく 429 + Retry-After ヘッダで返すよう `server.py:206-211` を修正。 |
| 検証 | (a) Redis 切断シミュレーションで 429 が返る、(b) 同一プロセス内の token bucket が枯渇後は 429、(c) 復旧後に自動回復 |
| 工数 | 2.0h |
| 依存 | なし |

### H4: SSE の `pubsub.get_message` 同期呼び出し対策

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/sse.py:62-82` |
| 問題 | `pubsub.get_message(timeout=1.0)` は同期呼び出しで 1 秒ブロック。イベントループ上で実行されるため他のリクエスト処理が停止する。 |
| 修正方針 | 1. `redis.asyncio` の `pubsub.get_message(timeout=...)` を使用(async 版に置換)。<br>2. `pubsub.listen()` の非同期イテレータを使い、タイムアウトは `asyncio.wait_for` で囲む。<br>3. ハートビートは `asyncio.sleep(15)` で代替。 |
| 検証 | 100 接続同時 SSE 時に他のルータが遅延しないこと、`locust` で 100 RPS でも p99 < 200ms |
| 工数 | 1.5h |
| 依存 | なし |

### H5: `CommercialPipeline.run` の非同期化とバックグラウンド化

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/routers/commercial.py:43`, `src/backend/workflows/commercial_pipeline.py` |
| 問題 | `await` 漏れで同期的に実行され、`subprocess.run` がイベントループをブロック。 |
| 修正方針 | 1. `CommercialPipeline.run` を `async def` に統一、内部の `subprocess.run` を `asyncio.to_thread` 経由へ。<br>2. ルータ側は Huey タスク化(即時 `task_id` 返却)。<br>3. 進捗は既存 SSE / `/api/tasks/{id}/status` を流用。 |
| 検証 | タイムアウトテスト、コネクション数モニタでループブロックがゼロ |
| 工数 | 2.0h |
| 依存 | なし |

### H6: narrative 系エンドポイントの認証付与

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/routers/narrative.py:65, 204` |
| 問題 | `override_affinity` / `rebuild_plot_with_foreshadows` が `require_api_key` を持っていない。 |
| 修正方針 | 1. 両エンドポイントに `Depends(require_api_key)` を追加。<br>2. `rebuild_plot_with_foreshadows` は長時間処理のため Huey タスク化(即時 202 + `task_id`)。 |
| 検証 | 認証無しで 401/403、タスクキューに正常登録 |
| 工数 | 1.0h |
| 依存 | なし |

### H7: RateLimitMiddleware の起動時 eager init

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/server.py:175-213` |
| 問題 | Redis 不在時の 503 が trace_id 付与前に返る上、初期化失敗が初回リクエスト遅延の原因。 |
| 修正方針 | 1. `lifespan` 内で `_redis_rate_limiter` を生成。<br>2. 起動時 ping 失敗時は起動は継続するが、`/health/ready` で degraded を返す。 |
| 検証 | 起動直後の最初のリクエストでも middleware 経路が同じ |
| 工数 | 1.0h |
| 依存 | なし |

### H8: Huey タスクのトランザクション境界統一

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/tasks.py:151-204, 445-498` |
| 問題 | Huey タスクごとに `try/except` が重複し、エラー時の状態保存とオーバーライド復元の両方がタスクごとに手書き。 |
| 修正方針 | 1. 共通デコレータ `@huey_task_with_cleanup` を作成して、設定オーバーライド保存/復元 + 例外時 ProgressState 保存を内包。<br>2. 全 Huey タスクに適用。 |
| 検証 | タスク例外発生時に `task_status:<id>` が `error` で永続化されること |
| 工数 | 1.5h |
| 依存 | C1 |

---

## Medium (P3: 2週間以内)

### M1: `router_helpers.workflow_endpoint` の TODO 解消

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/router_helpers.py:6-15` |
| 問題 | デコレータが素通りで、メトリクス/計装意図が宙に浮いている。 |
| 修正方針 | 1. 計装仕様を確定(`record_generation_task(workflow_type, "started")` 呼び出し)。<br>2. ワークフロー名 → メトリクス `workflow_type` のマッピングを実装。<br>3. `TODO` コメント削除。 |
| 検証 | 該当ルート呼び出しで Prometheus カウンタがインクリメント |
| 工数 | 0.5h |
| 依存 | なし |

### M2: `DatabaseConnectionWrapper` のデッドコード削除

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/database/core.py:138-152` |
| 問題 | `fetchone`/`fetchall` が明示的に `RuntimeError` を投げるのみで、利用すると即死。後方互換のための残骸。 |
| 修正方針 | メソッド削除。`DatabaseManager` の `fetch_one` / `fetch_all` 経路(既に存在)を推奨。 |
| 検証 | `grep -r "DatabaseConnectionWrapper"` の利用箇所が残っていないこと |
| 工数 | 0.2h |
| 依存 | なし |

### M3: `DataRepositoryFacade.__getattr__` のホワイトリスト化

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/database/repository.py:31-90` |
| 問題 | 動的解決で `illustrations` がリスト落ち、typo が AttributeError まで見えない。 |
| 修正方針 | 1. 許可リポジトリと許可メソッドを `frozenset` でホワイトリスト化。<br>2. 未許可は即 `AttributeError`。<br>3. `illustrations` を追加。 |
| 検証 | 不正メソッド名で即 `AttributeError`、イラスト系メソッドが正常動作 |
| 工数 | 1.0h |
| 依存 | なし |

### M4: 設定上書きの ContextVar 化(設計の確定版)

| 項目 | 内容 |
|------|------|
| ファイル | `config/settings.py`, `src/core/observability.py` |
| 問題 | C1 で ContextVar 化を行うが、ベースとなる `get_settings()` シグネチャと影響範囲を確定する必要あり。 |
| 修正方針 | 1. `SettingsProxy` クラスを導入し、`get_settings()` の戻り値を ContextVar 経由のラッパーに差し替え。<br>2. 既存の利用箇所は「プロキシ属性アクセス」で透過的に動作。<br>3. 書き込み API (`SettingsProxy.set_override`) を提供し、Huey タスクからのみ呼べる制限。 |
| 検証 | 既存テスト 100% パス、`settings.environment` の型ヒント保持 |
| 工数 | 3.0h |
| 依存 | C1 |

### M5: 旧 `execute` / `fetch_*` の完全削除

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/database/core.py:296-340` |
| 問題 | `enqueue_write` / `flush_writes` / `fetch_lastrowid` 等、生 SQL を期待するメソッドが残存。 |
| 修正方針 | 利用箇所を `grep` で確認 → 0 件なら削除。残っていれば Repository パターンへ移行。 |
| 検証 | 削除後のテスト緑、未参照を `vulture` で確認 |
| 工数 | 0.5h |
| 依存 | なし |

### M6: `WORKFLOW_REGISTRY` の明示化

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/workflows/__init__.py`, `src/backend/tasks.py:118-123` |
| 問題 | 動的 import ベースでワークフロー探索が読みにくい。 |
| 修正方針 | 1. `WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]]` を `workflows/__init__.py` に明示定義。<br>2. 各ワークフロークラスに `name: ClassVar[str]` を追加して登録を強制。 |
| 検証 | 全 method_name がレジストリに存在、未登録は起動時 fail |
| 工数 | 1.0h |
| 依存 | なし |

### M7: ルータ共通エラーハンドリング統一

| 項目 | 内容 |
|------|------|
| ファイル | 各 `src/backend/routers/*.py`(約 28 ファイル) |
| 問題 | `except Exception: raise HTTPException(500, str(e))` が散在し、内部情報漏洩 + ステータス不適切。 |
| 修正方針 | 1. 共通デコレータ `@route_errors` を作成(例外を `HegemonyError` / `AppError` / `ValidationError` へマップ)。<br>2. 既存 `error_handlers.py` に登録済みのハンドラにバトンを渡す。<br>3. ルータから個別 try/except を全削除。 |
| 検証 | 500 が詳細情報無しで返ること、想定例外で適切なステータス |
| 工数 | 3.0h |
| 依存 | なし |

### M8: `server.py` のハードコードバージョン削除

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/server.py:269` |
| 問題 | `version=settings.app_version if hasattr(settings, 'app_version') else "3.72"`。`pyproject.toml` は 3.5.0 で乖離。 |
| 修正方針 | `version` を `importlib.metadata.version("kaku-hegemony")` から取得。`getattr` フォールバックを削除。 |
| 検証 | `/docs` 上のバージョンが `pyproject.toml` と一致 |
| 工数 | 0.2h |
| 依存 | なし |

### M9: シャットダウン時の例外握りつぶし修正

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/server.py:125-127` |
| 問題 | `except (..., Exception)` の冗長な `Exception` を含む捕捉で、リソースリーク検出不能。 |
| 修正方針 | 1. `Exception` のみに統一。<br>2. `KeyboardInterrupt` / `SystemExit` は re-raise。<br>3. 個別リソースの close 失敗は `logger.error` + `metrics.inc("shutdown_errors")`。 |
| 検証 | モック close 失敗で `shutdown_errors` カウンタがインクリメント |
| 工数 | 0.3h |
| 依存 | なし |

### M10: `Lifespan` の DB 初期化を `init_db` から Alembic 統一

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/database/core.py:374-424`, `src/backend/server.py:83-86` |
| 問題 | `init_db` のフォールバックが「`PYTEST_CURRENT_TEST` を参照」するなど依存度が高い。 |
| 修正方針 | 1. `is_test_env` の判定を `Settings.environment` のみに統一。<br>2. `PYTEST_CURRENT_TEST` 依存を削除(テストは conftest で `Settings.environment="test"` を設定)。 |
| 検証 | テストモード判定の単体テスト |
| 工数 | 0.5h |
| 依存 | なし |

### M11: Huey SQLite フォールバックパスの外部化

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/worker_config.py:16-18` |
| 問題 | `src/backend/../../storage/db/...` のパスが固定。 |
| 修正方針 | `os.environ.get("HUEY_SQLITE_PATH", ...)` で上書き可能に。デフォルトは `storage/db/` 配下。 |
| 検証 | 環境変数でパス変更が反映 |
| 工数 | 0.2h |
| 依存 | なし |

### M12: バックエンドのテスト層整備

| 項目 | 内容 |
|------|------|
| ファイル | `tests/backend/`(現在 4 ファイル) |
| 問題 | `tests/backend/` 直下がほぼ空。`workflows/`, `routers/`, `tasks.py`, `engine_facade.py` のテストが不足。 |
| 修正方針 | 1. 既存 `IMPLEMENTATION_PLAN_DETAIL.md` のフェーズ0 (mock 整備) を完走。<br>2. 新規追加: `test_tasks_config_overrides.py` (C1/M4), `test_engine_facade.py` (H1), `test_workflow_registry.py` (M6), `test_uow_outbox.py` (回帰), `test_rate_limit_failover.py` (H3)。<br>3. 目標: `src/backend/` カバレッジ 19% → 60%。 |
| 検証 | `pytest tests/backend --cov=src/backend` で 60% 以上 |
| 工数 | 8.0h |
| 依存 | M3, M6 |

---

## Low (P4: バックログ)

### L1: `DataRepositoryFacade` の debug log 頻度削減

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/database/repository.py:38-86` |
| 問題 | メソッド呼び出しごとに `log.debug` 発火。高頻度パスで I/O 増。 |
| 修正方針 | `log.debug` を初回のみ、または `repr` ベースに変更。 |
| 工数 | 0.3h |

### L2: `engine_service.py` の配置整理

| 項目 | 内容 |
|------|------|
| ファイル | `src/engine_service.py` |
| 問題 | コア ↔ バックエンド境界が曖昧(`src/` 直下)。 |
| 修正方針 | `src/backend/engine_service.py` へ移動、import パス更新。 |
| 工数 | 0.5h |

### L3: レートリミットキー衝突リスクの継続対応

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/rate_limit.py`, `src/backend/auth.py:75-83` |
| 問題 | 既存 SHA-256 キーで衝突確率は低いが、長期間運用でのキー入れ替え手順が無い。 |
| 修正方針 | キーローテーション仕様を `docs/` に記述。自動的には行わない。 |
| 工数 | 0.5h |

### L4: `langgraph` 未インストール時の挙動改善

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/workflows/writing_langgraph.py:19-28` |
| 問題 | フォールバックが `None` を返すが、利用側で取り違えが起きると静かに失敗。 |
| 修正方針 | `HAS_LANGGRAPH = False` 時は `RuntimeError("WritingGraph requires langgraph")` を起動時に送出。 |
| 工数 | 0.3h |

### L5: `src/api/` の統合判断

| 項目 | 内容 |
|------|------|
| ファイル | `src/api/routes/ux_routes.py` |
| 問題 | 176 行のみで、`src/backend/routers/ux.py` に統合可能。 |
| 修正方針 | 移動 + `server.py` の登録更新。`src/api/` を撤去。 |
| 工数 | 0.5h |

### L6: API スキーマの Example 整備

| 項目 | 内容 |
|------|------|
| ファイル | `src/models/api_schemas.py` |
| 問題 | OpenAPI 仕様が薄く、SDK 自動生成時の UX が悪い。 |
| 修正方針 | 主要スキーマに `model_config = ConfigDict(json_schema_extra={...})` で Example を追加。 |
| 工数 | 1.0h |

### L7: 開発用 `make` ターゲット整備

| 項目 | 内容 |
|------|------|
| ファイル | `Makefile`(新規) |
| 問題 | `run_all.bat`, `start_app.sh` 等のスクリプトが散在。 |
| 修正方針 | `make dev / test / lint / migrate` を統一エントリに。既存スクリプトは deprecated 化。 |
| 工数 | 1.0h |

### L8: 設定の機微項目ログ除外ルール

| 項目 | 内容 |
|------|------|
| ファイル | `src/core/observability.py` |
| 問題 | `api_key[:4]` プレフィックス表示は OK だが、本文ログに混入するリスク。 |
| 修正方針 | `python-json-logger` のフィルタで `api_key`, `password`, `secret` を自動マスク。 |
| 工数 | 1.0h |

### L9: `engine.py` の import 順序整理

| 項目 | 内容 |
|------|------|
| ファイル | `src/backend/engine.py:1-37` |
| 問題 | TYPE_CHECKING ブロック + 通常 import が混在し、循環 import を誤魔化しがち。 |
| 修正方針 | 全プロトコル import を `src/core/interfaces.py` に集約。 |
| 工数 | 1.0h |

---

## 実行フェーズとマイルストーン

### フェーズ0: 準備 (0.5日 / 4h)
- ブランチ戦略: `feature/backend-hardening-2026q3`
- 影響範囲調査: `ProjectContext` 利用箇所のフル `grep`
- ベースライン測定: `pytest --cov=src/backend`、Prometheus スクレイピング
- レビュー観点ドキュメント作成: アーキチーム + セキュリティチーム

### フェーズ1: Critical (1.0日 / 5h)
- C1: 設定 ContextVar 化(2 コミット分割)
- C2: CORS 起動時検証強化
- C3: API キー `test*` フォールバック削除
- C4: ヘルスチェック LLM デフォルト無効化
- **マイルストーン**: 認証/設定/健全性関連の単体テスト + 統合テスト green

### フェーズ2: High (2.5日 / 16h)
- H1+H2: エンジン分解 (まとめて 1 PR)
- H3: RateLimit フェイルセーフ
- H4: SSE 同期呼び出し排除
- H5: CommercialPipeline バックグラウンド化
- H6: narrative 認証
- H7: middleware eager init
- H8: Huey デコレータ共通化
- **マイルストーン**: ベンチマーク比較(下記)で劣化ゼロ確認

### フェーズ3: Medium (2.5日 / 18.5h)
- M1〜M11 を独立 PR で順次
- M12: テスト拡充(他 M 完了後まとめて)
- **マイルストーン**: `src/backend/` カバレッジ 19% → 60%

### フェーズ4: Low (1.0日 / 7h)
- L1〜L9
- ドキュメント整備
- CHANGELOG 更新

---

## ベンチマーク・検証計画

| 指標 | ベースライン | 目標 | 測定方法 |
|------|--------------|------|----------|
| `/api/health` レスポンスタイム (Redis + DB + ChromaOK) | 現状測定 | < 50ms p99 | `locust` 100 RPS × 60s |
| `/api/tasks/{id}/stream` 同時接続数 | 現状測定 | 100 接続で CPU < 60% | SSE クライアント 100 並列 |
| `UltimateHegemonyEngine` 初期化時間 | 現状測定 | 改善 30% | `time.perf_counter` ベンチ |
| `src/backend/` テストカバレッジ | 19% | 60% | `coverage report` |
| `mypy` エラー数 | 0 (strict) | 0 維持 | `mypy src/backend` |
| `ruff` 違反数 | 0 | 0 維持 | `ruff check` |
| OpenAPI バージョン整合 | 不一致 | 一致 | 目視 + CI |

---

## リスクと代替案

| リスク | 影響 | 代替案/緩和策 |
|--------|------|----------------|
| ContextVar 化で既存テストが大量に壊れる | M4/C1 の中断 | フェーズ 0 で全利用箇所を列挙し、ラップ関数で段階移行 |
| エンジン分解でワークフローが動かなくなる | H1/H2 のロールバック | `EngineFacade` の旧 `@property` を 1 リリース `DeprecationWarning` で残す |
| RateLimit のトークンバケットがプロセス毎にバラつく | マルチワーカーで挙動不一致 | 最初は Redis ベースのまま、`HUEY_WORKERS=1` のみトークンバケット併用 |
| ヘルスチェック LLM 無効で真の障害検知が遅れる | C4 による誤検知防止の裏返し | `/health/ready?check=llm` をオンデマンドで叩けるよう管理用エンドポイント追加 |
| Huey デコレータの副作用互換性 | 既存タスクが動かない | `tests/integration/test_huey_tasks.py` を先に書き、振る舞いを固定化してから適用 |
| テスト拡充に時間がかかりすぎ | スケジュール遅延 | M12 を M3/M6 などの"実装と一緒に書く"戦略に変更し、増分を M の範囲に統合 |

---

## ロールバック戦略

各 PR は独立して revert 可能。`UltimateHegemonyEngine` 周りは特に:

1. `EngineFacade` 旧 `@property` を 1 リリース(2 週間)は残す
2. コンテキストマネージャ化は opt-in(`USE_CONTEXT_SETTINGS=true`)で展開
3. ヘルスチェックの LLM 無効化は機能フラグ(`KAKU_HEALTH_CHECK_LLM`)で制御

問題発生時は各機能フラグを false に戻すだけで旧挙動に復帰できる。

---

## 成果物

- 修正済みソースコード (PR 単位で 33 件)
- 更新されたテストスイート (新規 +30 ファイル / 目標 +60% カバー)
- OpenAPI 仕様書 (`/docs` 再生成)
- 運用 Runbook (`docs/runbook.md` 追記: フラグ一覧、ロールバック手順)
- アーキテクチャ図 (Mermaid 形式で `docs/architecture.md` 更新)
- CHANGELOG (機能フラグ・破壊的変更を明記)

---

## 完了条件 (DoD 再掲)

- [ ] 33 項目すべての PR がマージ済み、または明示的に「バックログへ」振り分け済み
- [ ] `pytest --cov=src/backend` で 60% 以上
- [ ] mypy / ruff / pre-commit が clean
- [ ] `/docs` のバージョンが `pyproject.toml` と一致
- [ ] ベンチマークで全項目ベースライン以内
- [ ] ステージング環境で 1 週間の soak test 通過
- [ ] セキュリティチームによる侵入テスト(レートリミット/認証)で問題なし

---

## 参考: 評価レポート → 計画のマッピング

| 評価レポート ID | 計画 ID | 件名 |
|-----------------|---------|------|
| 弱点#1 | H1, H2 | 神エンジン残置 |
| 弱点#2 | H1 | エンジン分割方針の不明確さ |
| 弱点#3 | C1, M4 | 設定のグローバル mutable |
| 弱点#4 | M3 | データアクセス層の二重構造 |
| 弱点#5 | M1 | `router_helpers` TODO 残し |
| 弱点#6 | C1 | `_apply_config_overrides` 二重呼び出し |
| 弱点#7 | M9 | `except (..., Exception)` 冗長 |
| 弱点#8 | H7 | middleware の lazy init |
| 弱点#9 | M2 | `DatabaseConnectionWrapper.fetchone` 死コード |
| 弱点#10 | M11 | Huey SQLite パス固定 |
| 弱点#11 | M12 | テスト偏在 |
| 弱点#12 | L1 | debug log 頻度 |
| 弱点#13 | C4 | ヘルスチェック LLM 過剰 |
| 弱点#14 | M8 | OpenAPI バージョン乖離 |
| 弱点#15 | C2 | CORS 検証の二重チェック |
| 弱点#16 | L5 | `src/api/` の有効性 |
| 弱点#17 | L2 | `engine_service.py` 配置 |
| 弱点#18 | M6 | `WORKFLOW_REGISTRY` 不在 |
| 弱点#19 | L6 | OpenAPI Example 不足 |

---

*作成日: 2026-08-29*
*対象コミット: HEAD (v3.5.0〜v3.7 系)*
*作成者: Kilo backend audit*
*次回レビュー: フェーズ 1 完了時点 (目安: 2026-09-05)*
