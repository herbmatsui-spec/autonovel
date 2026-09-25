# AutoNovel 実装計画書: コードレビュー是正と商用高信頼化（Hardening）計画 (20 Steps)

**策定日**: 2026-09-25  
**マスターSSOT**: [PHASE_ROADMAP_MASTER.md](file:///e:/hhh/plans/PHASE_ROADMAP_MASTER.md)  
**対象ブランチ**: `phase-master-integration`  
**目的**: 実施された包括コードレビューで特定された重大・高リスク所見（データベース層の並行性コミット欠陥、ヘルスチェックとルーティングの二重化乖離、Easy Mode 高負荷エンドポイントの認証欠落、LLMサーキットブレーカーの重複、`src/agent` ディレクトリ二重化、ルート直下の不要遺物）を段階的かつ安全に解消し、**全ステップでリグレッション防止テストを拡充・パスさせることで商用本番稼働（Phase 4）に耐えうる堅牢な基盤を確立する**。

---

## 📋 全体工程概要（20ステップ）

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Part 1: データベース層の並行性・トランザクション正常化 (Step 1〜4)               │
│  - BookRepository の非同期コミット欠陥解体 & 純粋 async 化                       │
│  - リグレッション防止テスト: test_book_repository_async_concurrency.py           │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Part 2: ルーティングとヘルスチェックの統合・一本化 (Step 5〜8)                  │
│  - src/api/health.py を src/backend/routers/health.py に完全集約                 │
│  - リグレッション防止テスト: test_server_health_integration.py (実アプリ疎通)   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Part 3: Easy Mode API のセキュリティ・認証強化 (Step 9〜12)                     │
│  - /gacha, /reverse-generate への API キー認証適用 & タイミング攻撃対策          │
│  - リグレッション防止テスト: test_easy_mode_security_guards.py                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Part 4: LLM クライアント・サーキットブレーカーの一元化 (Step 13〜15)            │
│  - src/services/llm/ を src/llm/ (RLock / ProviderHealthState) へ統合            │
│  - リグレッション防止テスト: test_circuit_breaker_concurrency.py                │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Part 5: レガシーシム・ディレクトリ二重化の完全解消 (Step 16〜18)                 │
│  - src/agent/ の src/agents/ への物理統合 & ルート直下 database/ 削除            │
│  - リグレッション防止テスト: test_clean_architecture_integrity.py               │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Part 6: 総合検証・回帰テストとドキュメント同期 (Step 19〜20)                     │
│  - 全リグレッションテストスイート一括実行 (ALL GREEN) & SSOT 更新・コミット      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 各ステップの詳細定義

### Part 1: データベース層の並行性・トランザクション正常化 (Step 1〜4)

#### Step 1: `BookRepository` の同期／非同期メソッド明確化と `_safe_commit` 廃止
- **目的**: 
  [src/backend/database/repository.py](file:///e:/hhh/src/backend/database/repository.py) にある `_safe_commit` / `_safe_refresh` 内の `loop.create_task(res)` による未待機バックグラウンドコミット、および `asyncio.run(res)` を完全撤廃し、非同期セッションでの明示的な `await session.commit()` を実現する。
- **対象ファイル**:
  - `src/backend/database/repository.py`
- **修正内容**:
  1. `_safe_commit` / `_safe_refresh` のハック的実装を削除。
  2. 非同期専用メソッド `async def commit_async(self) -> None` および `async def refresh_async(self, instance: Any) -> None` を定義し、`session` が `AsyncSession` の場合は正しく `await self.session.commit()` を行う。
  3. 同期コンテキストで呼び出された場合は同期 `self.session.commit()` を実行し、暗黙の並行タスク化を行わない。
  4. 非同期ルーターや Huey タスクから呼ばれるメソッド（`save_or_update_book_with_chapter` など）に `async` 版を提供。
- **リグレッション防止テスト**:
  - 新規作成: `tests/database/test_book_repository_async_concurrency.py`
  - テストケース: `test_book_repository_async_commit_waits_for_completion`
  - テストケース: `test_book_repository_sync_session_commits_properly`
- **検証コマンド**:
  ```bash
  pytest tests/database/test_book_repository_async_concurrency.py -v
  ```
- **期待結果**: コミット待機漏れ・例外の握りつぶしが発生しないこと。

#### Step 2: `BookRepository.update_task_status` および `create_task` の非同期対応
- **目的**: 
  タスク作成・ステータス更新処理において、非同期コンテキストでの安全な書き込みを保証する。
- **対象ファイル**:
  - `src/backend/database/repository.py`
- **修正内容**:
  1. `create_task_async` および `update_task_status_async` を追加。
  2. 既存の `create_task` / `update_task_status` は同期セッション使用時の後方互換性メソッドとして維持。
- **リグレッション防止テスト**:
  - `tests/database/test_book_repository_async_concurrency.py`
  - テストケース: `test_create_and_update_task_status_async`
- **検証コマンド**:
  ```bash
  pytest tests/database/test_book_repository_async_concurrency.py -v
  ```
- **期待結果**: 非同期セッションでタスクの作成とステータス更新が確実にDBへ永続化されること。

#### Step 3: `easy_mode.py` におけるリポジトリ呼び出しの整合化
- **目的**: 
  [src/backend/routers/easy_mode.py](file:///e:/hhh/src/backend/routers/easy_mode.py) 内の `BookRepository` 利用箇所（行 284, 325, 386, 482）で、セッション引数と同期／非同期メソッド呼び出しを統一する。
- **対象ファイル**:
  - `src/backend/routers/easy_mode.py`
- **修正内容**:
  1. 行 386 の `cancel_task` で `repo = BookRepository()` と引数なしで呼んでいる箇所を、Depends で注入されたセッションまたは `DatabaseManager` を渡すように修正。
  2. 非同期ハンドラ内でのタスク作成・更新を `await repo.create_task_async(...)` / `await repo.update_task_status_async(...)` に移行。
- **リグレッション防止テスト**:
  - `tests/api/test_real_easy_mode_api.py`
  - テストケース: `test_easy_mode_generate_enqueues_task`
  - テストケース: `test_easy_mode_cancel_task_persists_status`
- **検証コマンド**:
  ```bash
  pytest tests/api/test_real_easy_mode_api.py -v
  ```
- **期待結果**: 全テスト PASS、エラーなし。

#### Step 4: データベース並行トランザクション検証
- **目的**: 
  複数リクエストが同時に `BookRepository` を利用した際に、SQLite WALモード / PostgreSQL でロックや接続枯渇が発生しないことを検証する。
- **対象ファイル**:
  - `tests/database/test_book_repository_async_concurrency.py`
- **修正内容**:
  - `asyncio.gather` で 10 件の並行エピソード保存・タスク更新を行う負荷テストを追加。
- **検証コマンド**:
  ```bash
  pytest tests/database/test_book_repository_async_concurrency.py -v
  ```
- **期待結果**: 10並行実行が例外なく正常完了すること。

---

### Part 2: ルーティングとヘルスチェックの統合・一本化 (Step 5〜8)

#### Step 5: `src/api/health.py` の 503 ハンドリングを `src/backend/routers/health.py` へ集約
- **目的**: 
  二重化しているヘルスチェック実装を [src/backend/routers/health.py](file:///e:/hhh/src/backend/routers/health.py) に集約し、[src/api/health.py](file:///e:/hhh/src/api/health.py) の未マウント状態を解消する。
- **対象ファイル**:
  - `src/backend/routers/health.py`
  - `src/api/health.py`
- **修正内容**:
  1. `src/backend/routers/health.py` に `/health/live` および `/health/ready` のエイリアスルートを追加。
  2. `check_database` 実行結果が異常（エラーまたは例外）の場合、確実に `HTTP 503 Service Unavailable` を返却するレスポンスを実装。
  3. `src/api/health.py` は `src/backend/routers/health.py` からルーターをインポートして再エクスポートする薄いシムに変更。
- **リグレッション防止テスト**:
  - 更新: `tests/api/test_health_real.py`（インポート元を `src.backend.routers.health` に更新）
- **検証コマンド**:
  ```bash
  pytest tests/api/test_health_real.py -v
  ```
- **期待結果**: `/health/live` で 200、`/health/ready` で DB 正常時 200・異常時 503 が返却されること。

#### Step 6: `src/backend/server.py` のヘルスチェックルーティング整理
- **目的**: 
  [src/backend/server.py](file:///e:/hhh/src/backend/server.py) 内の `@app.get("/health")` と `app.include_router(health.router)` の役割分担を明確にし、本番監視（Kubernetes / Docker 等）が期待する規格へ準拠させる。
- **対象ファイル**:
  - `src/backend/server.py`
- **修正内容**:
  1. `health.router`（`prefix=""`）をメインサーバーにマウントし、以下の標準エンドポイントを公開：
     - `/health` (総合ヘルスチェック)
     - `/health/live` および `/health/liveness` (Liveness probe: 即座に 200)
     - `/health/ready` および `/health/readiness` (Readiness probe: DB/外部依存健全性、異常時 503)
     - `/health/detail` (全コンポーネント詳細)
  2. 重複するルート定義を排除。
- **リグレッション防止テスト**:
  - 新規作成: `tests/api/test_server_health_integration.py`
- **検証コマンド**:
  ```bash
  pytest tests/api/test_server_health_integration.py -v
  ```
- **期待結果**: メインサーバーインスタンスに対してすべてのヘルスプローブが正しく応答すること。

#### Step 7: 実アプリ疎通テストスイート作成 (`test_server_health_integration.py`)
- **目的**: 
  スタンドアロンの仮設 FastAPI ではなく、本番構成の `src.backend.server.app` を直接 TestClient でテストし、ミドルウェア（`GlobalAuthMiddleware`）との干渉を検証する。
- **対象ファイル**:
  - `tests/api/test_server_health_integration.py` (新規作成)
- **テストケース**:
  1. `test_server_health_live_probe_unauthenticated`: 認証なしで `/health/live` が 200 を返すこと（GlobalAuthMiddleware で遮断されないこと）。
  2. `test_server_health_ready_probe_database_ok`: DB 正常時に `/health/ready` が 200 を返すこと。
  3. `test_server_health_ready_probe_database_fail_returns_503`: DB 異常時に `/health/ready` が 503 を返すこと。
  4. `test_server_root_health_returns_ok`: `/health` が総合ステータスを返すこと。
- **検証コマンド**:
  ```bash
  pytest tests/api/test_server_health_integration.py -v
  ```
- **期待結果**: 全 4 テスト PASS。

#### Step 8: ヘルスチェック旧テストスイートの同期更新
- **目的**: 
  既存の `tests/api/test_health_real.py` を最新の統合ルーター仕様に合わせ、古いパスへの依存を解消する。
- **対象ファイル**:
  - `tests/api/test_health_real.py`
- **検証コマンド**:
  ```bash
  pytest tests/api/test_health_real.py tests/api/test_server_health_integration.py -v
  ```
- **期待結果**: 両スイートとも ALL GREEN。

---

### Part 3: Easy Mode API のセキュリティ・認証強化 (Step 9〜12)

#### Step 9: 高負荷エンドポイントへの API キー認証依存性の注入
- **目的**: 
  [src/backend/routers/easy_mode.py](file:///e:/hhh/src/backend/routers/easy_mode.py) の高負荷・LLM 実行エンドポイントに認証ガードを追加する。
- **対象ファイル**:
  - `src/backend/routers/easy_mode.py`
- **修正内容**:
  1. `gacha_endpoint` (`/easy_mode/gacha`): `api_key: str = Depends(require_api_key)` を追加。
  2. `reverse_generate_endpoint` (`/easy_mode/reverse-generate`): `api_key: str = Depends(require_api_key)` を追加。
  3. `cancel_task` (`/easy_mode/task/{task_id}`): `api_key: str = Depends(require_api_key)` を追加。
- **リグレッション防止テスト**:
  - 新規作成: `tests/api/test_easy_mode_security_guards.py`
- **検証コマンド**:
  ```bash
  pytest tests/api/test_easy_mode_security_guards.py -v
  ```
- **期待結果**: 認証ヘッダーなしで 401 Unauthorized、正しい API キー付与で 200 を返却すること。

#### Step 10: `validate_api_key_sync` のタイミング攻撃脆弱性是正
- **目的**: 
  [src/backend/auth.py](file:///e:/hhh/src/backend/auth.py) の API キー検証において、`api_key in allowed_keys` の文字列比較を暗号学的に安全な定数時間比較に改善する。
- **対象ファイル**:
  - `src/backend/auth.py`
- **修正内容**:
  ```python
  import hmac
  # 修正前: if not allowed_keys or api_key not in allowed_keys:
  # 修正後:
  is_valid = any(hmac.compare_digest(api_key, k) for k in allowed_keys)
  if not allowed_keys or not is_valid:
      return False
  ```
- **リグレッション防止テスト**:
  - `tests/security/test_auth_timing_safety.py` (新規作成)
  - テストケース: `test_validate_api_key_constant_time_comparison`
  - テストケース: `test_validate_api_key_with_whitespace_and_invalid_tokens`
- **検証コマンド**:
  ```bash
  pytest tests/security/test_auth_timing_safety.py -v
  ```
- **期待結果**: 全テスト PASS。

#### Step 11: タスク操作エンドポイント (`cancel_task`) の入力検証強化
- **目的**: 
  不正な形式の `task_id`（パストラバーサルや空文字など）に対する防御を追加する。
- **対象ファイル**:
  - `src/backend/routers/easy_mode.py`
- **修正内容**:
  `task_id: str = Path(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_\-]+$")` によるバリデーションを付与。
- **リグレッション防止テスト**:
  - `tests/api/test_easy_mode_security_guards.py`
  - テストケース: `test_cancel_task_rejects_malformed_task_id`
- **検証コマンド**:
  ```bash
  pytest tests/api/test_easy_mode_security_guards.py -v
  ```
- **期待結果**: 不正な `task_id` に対し 422 Unprocessable Entity を返すこと。

#### Step 12: セキュリティ統合テストの実行
- **目的**: 
  Easy Mode の全エンドポイントに対する認証・認可・入力検証のセーフティネットを確認。
- **対象ファイル**:
  - `tests/api/test_real_easy_mode_api.py`
  - `tests/api/test_easy_mode_security_guards.py`
- **検証コマンド**:
  ```bash
  pytest tests/api/test_real_easy_mode_api.py tests/api/test_easy_mode_security_guards.py -v
  ```
- **期待結果**: すべてのセキュリティテストが ALL GREEN。

---

### Part 4: LLM クライアント・サーキットブレーカーの一元化 (Step 13〜15)

#### Step 13: `src/services/llm/circuit_breaker.py` を `src/llm/` 側の実装へ統合
- **目的**: 
  `src/services/llm/circuit_breaker.py` にある単一グローバル状態の簡易サーキットブレーカーを廃止し、スレッドセーフ（`RLock`）かつプロバイダごとに状態を分離できる [src/llm/circuit_breaker.py](file:///e:/hhh/src/llm/circuit_breaker.py) の `LLMCircuitBreaker` へ一本化する。
- **対象ファイル**:
  - `src/services/llm/circuit_breaker.py`
- **修正内容**:
  1. `src/services/llm/circuit_breaker.py` の内部実装を `from src.llm.circuit_breaker import LLMCircuitBreaker, CircuitState, CircuitBreakerOpenException` からの継承・ラッパーにし、後方互換性を保持しつつ堅牢な実装へ委譲。
  2. シングルトンまたはインスタンス生成時にプロバイダ個別追跡が有効になるように連携。
- **リグレッション防止テスト**:
  - 新規作成: `tests/llm/test_circuit_breaker_concurrency.py`
- **検証コマンド**:
  ```bash
  pytest tests/llm/test_circuit_breaker_concurrency.py -v
  ```
- **期待結果**: スレッドセーフ性、プロバイダごとの障害分離（Gemini が落ちても OpenAI は生かす）が正常動作すること。

#### Step 14: `src/services/llm/factory.py` のサーキットブレーカー参照更新
- **目的**: 
  LLM アダプタファクトリが統合後の `LLMCircuitBreaker` を利用してプロバイダ別の健全性を正しく追跡するようにする。
- **対象ファイル**:
  - `src/services/llm/factory.py`
- **修正内容**:
  アダプタ生成時およびリクエスト実行時にプロバイダ名を指定してサーキット状態を判定・更新するロジックを接続。
- **リグレッション防止テスト**:
  - `tests/llm/test_circuit_breaker_concurrency.py`
  - テストケース: `test_factory_uses_unified_circuit_breaker`
- **検証コマンド**:
  ```bash
  pytest tests/llm/test_circuit_breaker_concurrency.py -v
  ```
- **期待結果**: 全テスト PASS。

#### Step 15: サーキットブレーカー回帰検証
- **目的**: 
  Easy Mode パイプラインおよび既存の LLM 関連テストが壊れていないことを確認。
- **対象テスト**:
  - `tests/e2e/test_easy_mode_flow.py`
  - `tests/test_conftest_fixtures.py`
  - `tests/llm/test_circuit_breaker_concurrency.py`
- **検証コマンド**:
  ```bash
  pytest tests/e2e/test_easy_mode_flow.py tests/test_conftest_fixtures.py tests/llm/test_circuit_breaker_concurrency.py -v
  ```
- **期待結果**: 全テスト PASS。

---

### Part 5: レガシーシム・ディレクトリ二重化の完全解消 (Step 16〜18)

#### Step 16: `src/agent/` 内モジュールの `src/agents/` への完全移行
- **目的**: 
  [src/agent/](file:///e:/hhh/src/agent) 配下にある `hooks/`, `memory/`, `tools/` の実装を精査し、[src/agents/](file:///e:/hhh/src/agents) 側に不足している要素があればマージした上で、`src/agent/` 配下のサブディレクトリを削除し、単一の互換性転送シム [src/agent/__init__.py](file:///e:/hhh/src/agent/__init__.py) のみに縮小する。
- **対象ファイル**:
  - `src/agent/hooks/`
  - `src/agent/memory/`
  - `src/agent/tools/`
  - `src/agent/__init__.py`
- **修正内容**:
  1. `src/agent/` 配下のサブディレクトリ・ファイルを物理削除。
  2. `src/agent/__init__.py` は `from src.agents import *` のみを提供する非推奨シムとして維持。
- **リグレッション防止テスト**:
  - 新規作成: `tests/infrastructure/test_clean_architecture_integrity.py`
  - テストケース: `test_src_agent_imports_resolve_to_agents`
- **検証コマンド**:
  ```bash
  pytest tests/infrastructure/test_clean_architecture_integrity.py -v
  ```
- **期待結果**: `src.agent` からの import が壊れずにすべて `src.agents` に解決されること。

#### Step 17: ルート直下の不要遺物・空ファイルの物理削除
- **目的**: 
  不要な混乱とバグを招くルート直下の古い同期専用 [database/core.py](file:///e:/hhh/database/core.py)、および `config/` 内の 0 バイトファイル（`data_loader.py`, `domain_profiles.py`）を物理削除する。
- **対象ファイル**:
  - `database/core.py` (ルート直下)
  - `database/` (空ディレクトリ)
  - `config/data_loader.py` (0バイト)
  - `config/domain_profiles.py` (0バイト)
- **修正内容**:
  1. 該当ファイルを git から物理削除。
  2. プロジェクト内でルート直下の `database.core` を参照している古い import がないか走査・確認。
- **リグレッション防止テスト**:
  - `tests/infrastructure/test_package_imports.py`
  - `tests/infrastructure/test_clean_architecture_integrity.py`
  - テストケース: `test_no_broken_database_imports_across_project`
- **検証コマンド**:
  ```bash
  pytest tests/infrastructure/test_package_imports.py tests/infrastructure/test_clean_architecture_integrity.py -v
  ```
- **期待結果**: プロジェクト内の全モジュールインポートが正常に通過すること。

#### Step 18: クリーンアーキテクチャ整合性テストスイートの確定
- **目的**: 
  今後新たな二重化ファイルや不正な依存が混入しないよう、静的整合性チェッカーをテストスイートに組み込む。
- **対象ファイル**:
  - `tests/infrastructure/test_clean_architecture_integrity.py`
- **検証コマンド**:
  ```bash
  pytest tests/infrastructure/test_clean_architecture_integrity.py -v
  ```
- **期待結果**: 全テスト PASS。

---

### Part 6: 総合検証・回帰テストとドキュメント同期 (Step 19〜20)

#### Step 19: 全リグレッションテストスイートの一括実行
- **目的**: 
  既存の13テストスイートに加え、本計画で新規作成した全テスト（計18スイート以上）を一括実行し、完全な ALL GREEN と実行速度（3秒以内目標）を実証する。
- **対象テスト一覧**:
  1. `tests/config/test_project_context_integrity.py`
  2. `tests/infrastructure/test_package_imports.py`
  3. `tests/test_conftest_fixtures.py`
  4. `tests/api/test_real_easy_mode_api.py`
  5. `tests/audit/test_static_rules_crlf.py`
  6. `tests/audit/test_unified_llm_auditor_robustness.py`
  7. `tests/generation/test_local_polish_sanitization.py`
  8. `tests/generation/test_pdca_pipeline_integration.py`
  9. `tests/generation/test_cache_lru.py`
  10. `tests/api/test_health_real.py`
  11. `tests/e2e/test_easy_mode_flow.py`
  12. `tests/audit/test_unified_auditor_equivalence.py`
  13. `tests/infrastructure/test_monitoring_init.py`
  14. `tests/database/test_book_repository_async_concurrency.py` (新規)
  15. `tests/api/test_server_health_integration.py` (新規)
  16. `tests/api/test_easy_mode_security_guards.py` (新規)
  17. `tests/security/test_auth_timing_safety.py` (新規)
  18. `tests/llm/test_circuit_breaker_concurrency.py` (新規)
  19. `tests/infrastructure/test_clean_architecture_integrity.py` (新規)
- **検証コマンド**:
  ```bash
  pytest tests/config/test_project_context_integrity.py tests/infrastructure/test_package_imports.py tests/test_conftest_fixtures.py tests/api/test_real_easy_mode_api.py tests/audit/test_static_rules_crlf.py tests/audit/test_unified_llm_auditor_robustness.py tests/generation/test_local_polish_sanitization.py tests/generation/test_pdca_pipeline_integration.py tests/generation/test_cache_lru.py tests/api/test_health_real.py tests/e2e/test_easy_mode_flow.py tests/audit/test_unified_auditor_equivalence.py tests/infrastructure/test_monitoring_init.py tests/database/test_book_repository_async_concurrency.py tests/api/test_server_health_integration.py tests/api/test_easy_mode_security_guards.py tests/security/test_auth_timing_safety.py tests/llm/test_circuit_breaker_concurrency.py tests/infrastructure/test_clean_architecture_integrity.py -v
  ```
- **期待結果**: 全テストケース PASS（`0 failed, 0 errors`）。

#### Step 20: マスターロードマップ同期と変更コミット
- **目的**: 
  [plans/PHASE_ROADMAP_MASTER.md](file:///e:/hhh/plans/PHASE_ROADMAP_MASTER.md) に本計画の実施状況と達成実績を反映し、コミットを作成する。
- **対象ファイル**:
  - `plans/PHASE_ROADMAP_MASTER.md`
  - `plans/PLAN_CODE_REVIEW_REMEDIATION_AND_HARDENING.md`
- **実行コマンド**:
  ```bash
  git add plans/
  git commit -m "docs: define code review remediation and hardening execution plan with regression tests"
  ```
- **期待結果**: 作業ツリーがクリーンになり、SSOT が最新化されること。

---

## 🛡️ リグレッション防止マトリクス

本計画で追加・更新されるリグレッション防止テストと防止対象の対応表です：

| テストスイート | 検証対象コンポーネント | 防止するリグレッション・障害 |
| :--- | :--- | :--- |
| `tests/database/test_book_repository_async_concurrency.py` | `BookRepository` | コミット未待機によるデータ不整合、HTTP接続切断後のSessionError |
| `tests/api/test_server_health_integration.py` | `src/backend/server.py` | メインサーバーとヘルスチェック仕様の乖離、認証ミドルウェアによるプローブ遮断 |
| `tests/api/test_easy_mode_security_guards.py` | `src/backend/routers/easy_mode.py` | ガチャ・逆算生成への不正アクセス、悪意あるタスクキャンセル |
| `tests/security/test_auth_timing_safety.py` | `src/backend/auth.py` | タイミング攻撃によるAPIキー漏洩、不正トークン通過 |
| `tests/llm/test_circuit_breaker_concurrency.py` | `LLMCircuitBreaker` | マルチスレッド環境での競合状態、単一プロバイダ障害時の連鎖遮断 |
| `tests/infrastructure/test_clean_architecture_integrity.py` | 全体パッケージ構造 | 削除モジュールへの先祖返りインポート、二重化ファイルの再混入 |

---

## ⚠️ リスクとロールバック基準

1. **DB移行時のリスク**:
   - 万が一非同期化により既存の同期呼び出し（古いワークフロー等）でエラーが出た場合は、`BookRepository` に明示的な同期ラッパーメソッドを残して段階的に移行する。
2. **ヘルスチェック統合時のリスク**:
   - Kubernetes や Docker Compose の既存ヘルスチェック設定が `/health`、`/health/live`、`/health/liveness` のいずれを参照していても疎通するよう、エイリアスルートをすべて維持する。
3. **ロールバック基準**:
   - いずれかのステップ実行後に既存の40テストのうち1つでも破綻し、15分以内に原因特定できない場合は直前のコミットへ `git checkout` で戻す。
