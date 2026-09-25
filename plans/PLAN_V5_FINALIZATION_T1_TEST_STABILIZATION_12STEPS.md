# AutoNovel v5系完成化 実装計画書【T1】
# テスト基盤の完全安定化と残存失敗テスト解消（ALL GREEN & リグレッション防止）

- **文書ID**: PLAN_V5_FINALIZATION_T1_TEST_STABILIZATION_12STEPS
- **作成日**: 2026-09-25
- **対象バージョン**: AutoNovel v5.2.0 (v5系最終完成形)
- **関連ドキュメント**: [PHASE_ROADMAP_MASTER.md](file:///e:/hhh/plans/PHASE_ROADMAP_MASTER.md), [failnow_analysis.md](file:///e:/hhh/docs/failnow_analysis.md)

---

## 1. 概要と目的

本計画書は、AutoNovel v5系を一応の完成形（商用・安定版）とするための最優先タスクである**「テスト基盤の完全安定化」**を達成するための実行計画書です。

現在、約2,700件のテストがパスしている一方で、[fail_now.txt](file:///e:/hhh/fail_now.txt) に記録されている **45件の失敗・11件のエラー** が残存しています。また、テスト実行環境の設定（`pytest.ini` のプラグイン依存）に不整合があり、ローカル実行時の障害となっています。

本計画では、環境の是正、残存失敗テストの完全解消（ALL GREEN達成）、および将来の機能追加や微修正で主要機能が破壊されないための**「リグレッション防止テストスイート」**を新設します。

---

## 2. 12の実行ステップ

```
[環境是正]               [残存失敗テスト解消]                                                [リグレッション防止・CI]
Step 1: pytest環境是正 ──► Step 2: Stripe Webhook ──► Step 3: なろうPublisher ──► Step 4: Eroticパイプライン
                        ──► Step 5: DB並行性      ──► Step 6: SQLite RAG      ──► Step 7: マルチメディアDB
                        ──► Step 8: マーケティング ──► Step 9: グラフRAGスタブ  ──► Step 10: 執筆パイプライン整合テスト
                                                                                ──► Step 11: DB/認証/課金不変テスト
                                                                                ──► Step 12: CI統合 & ALL GREEN検証
```

### Step 1: `pytest.ini` のプラグイン依存不整合解消とテスト実行環境の整備
- **対象ファイル**:
  - [pytest.ini](file:///e:/hhh/pytest.ini)
  - [pyproject.toml](file:///e:/hhh/pyproject.toml)
- **作業内容**:
  1. `pytest.ini` の `addopts` に指定されている `--timeout=60` は `pytest-timeout` が未インストールの環境で構文エラーとなるため、`pyproject.toml` の `dev` 依存に `pytest-timeout>=2.2.0` を明記。
  2. 万一プラグイン未導入時でもテストが落ちないよう、`pytest.ini` 側でオプショナルフラグとして定義するか、基本設定を整理。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_container.py
  ```
  *(エラーなくテストが収集・実行されること)*

---

### Step 2: Stripe 決済 Webhook 非同期トランザクションテストの修復
- **対象ファイル**:
  - [src/backend/routers/billing_webhook.py](file:///e:/hhh/src/backend/routers/billing_webhook.py)
  - [tests/unit/services/test_stripe_payment.py](file:///e:/hhh/tests/unit/services/test_stripe_payment.py)
- **作業内容**:
  1. `billing_webhook.py` のイベント処理におけるコルーチン関数呼び出し（`CreditService` や DB セッションコミット）の `await` 漏れを修正。
  2. `test_stripe_payment.py` のモック設定（`mock_session.execute` の戻り値およびスカラー解決）を SQLAlchemy 2.0 AsyncSession の非同期仕様に完全に整合。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/services/test_stripe_payment.py -v
  ```

---

### Step 3: 小説家になろう Publisher の外部依存モック隔離
- **対象ファイル**:
  - [src/services/publishers/narou.py](file:///e:/hhh/src/services/publishers/narou.py)
  - [tests/unit/publishers/test_narou.py](file:///e:/hhh/tests/unit/publishers/test_narou.py)
- **作業内容**:
  1. `test_narou.py` で発生している 11 件の ERROR（Selenium / ChromeDriverManager インポートおよび初期化依存）を解消。
  2. `narou.py` 内で selenium が未インストールの場合のインポートガード（`try-except ImportError`）を強化。
  3. `test_narou.py` のフィクスチャでブラウザドライバの生成処理を完全に Mock 化し、実ブラウザやバイナリが存在しないヘッドレス CI 環境でも確実にパスするよう修復。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/publishers/test_narou.py -v
  ```

---

### Step 4: エロティックパイプラインの Pydantic モデル・境界値整合
- **対象ファイル**:
  - [src/agents/erotic/](file:///e:/hhh/src/agents/erotic/)
  - [tests/unit/agents/test_erotic_pipeline.py](file:///e:/hhh/tests/unit/agents/test_erotic_pipeline.py)
  - [tests/unit/test_erotic_baseline.py](file:///e:/hhh/tests/unit/test_erotic_baseline.py)
- **作業内容**:
  1. `test_erotic_pipeline.py`（23件）および `test_erotic_baseline.py`（2件）の失敗原因（Pydantic v2 モデルへの移行に伴う型変換エラー、スタミナ・心理推移のバリデーション境界値）を修正。
  2. `EroticCurve` の強度フェーズ計算ロジックと `ContinuityTracker` の状態管理アサーションを最新の実装コードに整合。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/agents/test_erotic_pipeline.py tests/unit/test_erotic_baseline.py -v
  ```

---

### Step 5: 非同期 DB・リポジトリ並行アクセスセッション競合の解消
- **対象ファイル**:
  - [src/backend/database/unit_of_work.py](file:///e:/hhh/src/backend/database/unit_of_work.py)
  - [tests/unit/test_repository_concurrency.py](file:///e:/hhh/tests/unit/test_repository_concurrency.py)
  - [tests/unit/test_uow_repositories.py](file:///e:/hhh/tests/unit/test_uow_repositories.py)
- **作業内容**:
  1. `test_repository_get_set_state_async` における複数並行タスクによる同一非同期セッション操作の競合を防止（セッションファクトリ経由の分離）。
  2. `test_uow_all_repositories_instantiate_without_name_error` で発生している未定義リポジトリ名エラーの解消と UoW キャッシュクリーンアップ処理の正常化。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_repository_concurrency.py tests/unit/test_uow_repositories.py -v
  ```

---

### Step 6: SQLite RAG Embedding のバッチ検索・バックフィル修復
- **対象ファイル**:
  - [src/services/rag/sqlite_rag_service.py](file:///e:/hhh/src/services/rag/sqlite_rag_service.py)
  - [tests/unit/test_sqlite_rag_embedding.py](file:///e:/hhh/tests/unit/test_sqlite_rag_embedding.py)
- **作業内容**:
  1. `test_sqlite_rag_batch_vector_search_and_no_truncation` のベクトル長ミスマッチおよびトランケーション不整合を修正。
  2. `test_backfill_missing_embeddings` における未埋め込みチャンクの検知と非同期バッチ更新ロジックを修正。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_sqlite_rag_embedding.py -v
  ```

---

### Step 7: タスク・マルチメディア実DBテストの修復
- **対象ファイル**:
  - [src/backend/routers/tasks.py](file:///e:/hhh/src/backend/routers/tasks.py)
  - [src/backend/routers/multimedia.py](file:///e:/hhh/src/backend/routers/multimedia.py)
  - [tests/unit/test_p4_async_and_db_concurrency.py](file:///e:/hhh/tests/unit/test_p4_async_and_db_concurrency.py)
  - [tests/unit/test_multimedia_real_db.py](file:///e:/hhh/tests/unit/test_multimedia_real_db.py)
  - [tests/unit/test_multimedia_tasks.py](file:///e:/hhh/tests/unit/test_multimedia_tasks.py)
- **作業内容**:
  1. `test_get_task_status_uses_async_redis` の Redis モックと async/await 呼び出しの整合。
  2. `test_empty_book_router_returns_422` のステータスコード整合（バリデーションエラーの 422 判定）。
  3. `test_generate_asset_pack_task_runs_sync` の Huey タスク同期実行フォールバックの動作保証。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_p4_async_and_db_concurrency.py tests/unit/test_multimedia_real_db.py tests/unit/test_multimedia_tasks.py -v
  ```

---

### Step 8: マーケティング・エンリッチメント・音声パイプラインテストの修復
- **対象ファイル**:
  - [tests/unit/marketing/test_marketing_ctr_router.py](file:///e:/hhh/tests/unit/marketing/test_marketing_ctr_router.py)
  - [tests/unit/test_marketing_agent.py](file:///e:/hhh/tests/unit/test_marketing_agent.py)
  - [tests/unit/test_enrichment_phase4_step55_60.py](file:///e:/hhh/tests/unit/test_enrichment_phase4_step55_60.py)
  - [tests/unit/test_voicevox_pipeline.py](file:///e:/hhh/tests/unit/test_voicevox_pipeline.py)
- **作業内容**:
  1. `test_generate_viral_titles_endpoint` および `test_post_export_package_endpoint` の Pydantic スキーマ整合。
  2. `test_step56_llm_sensory_generation_call` の LLM モック呼び出し引数の検証修正。
  3. `test_speaker_mapper` の話者マッピングテーブルとデフォルト ID のアサーション修正。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/marketing/test_marketing_ctr_router.py tests/unit/test_marketing_agent.py tests/unit/test_enrichment_phase4_step55_60.py tests/unit/test_voicevox_pipeline.py -v
  ```

---

### Step 9: グラフ RAG（Apache AGE廃止後）テストの整合と孤立スタブのクリーンアップ
- **対象ファイル**:
  - [src/services/age_client.py](file:///e:/hhh/src/services/age_client.py)
  - [tests/unit/test_graphrag.py](file:///e:/hhh/tests/unit/test_graphrag.py)
- **作業内容**:
  1. Apache AGE は既に廃止され ChromaDB / リレーショナルメモリへ完全移行しているため、`test_graphrag.py` 内の不要な旧 AGE 接続テストを ChromaDB / SQLite リレーショナル検索テストへ更新、または安全に隔離。
  2. `test_graph_pipeline_service` の引数型エラーを解消。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_graphrag.py -v
  ```

---

### Step 10: 【リグレッション防止テスト】執筆コア・二段階プロット・4層圧縮 統合不変性テストの実装
- **新規作成ファイル**:
  - `tests/regression/test_v5_pipeline_integrity.py`
- **テスト設計**:
  * **テスト1**: `test_coarse_fine_expansion_flow`
    * `EpisodeMacroSkeleton` から `PlotMicroBlueprint` への JIT 展開が、LLM モック経由で 1 回で確実に実行され、ビート・五感・演出指示が生成されること。
  * **テスト2**: `test_four_layer_compression_invariants`
    * レイヤー1（静的トリミング）〜レイヤー4（セマンティック要約）の圧縮が実行され、コンテキスト長が規定サイズ以下に収まり、必須アンカー（登場人物名・直前イベント）が欠落しないこと。
  * **テスト3**: `test_quality_loop_single_patch_limit`
    * 監査後の推敲（PDCA）ループが無限ループにならず、最大 1 回の局所パッチ（Single-shot Polish）で収束すること。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_pipeline_integrity.py -v
  ```

---

### Step 11: 【リグレッション防止テスト】DBトランザクション・認証RBAC・決済整合性テストの実装
- **新規作成ファイル**:
  - `tests/regression/test_v5_critical_invariants.py`
- **テスト設計**:
  * **テスト1**: `test_db_session_commit_isolation`
    * 複数リポジトリが関与するトランザクションにおいて、1 つが失敗した際に全操作がロールバックされ、データ不整合が起きないこと。
  * **テスト2**: `test_jwt_and_timing_safe_auth`
    * 認証トークン検証が定数時間比較（`hmac.compare_digest`）で行われ、改ざんトークンが 401 で弾かれること。
  * **テスト3**: `test_billing_webhook_idempotency`
    * 同一の Stripe イベント ID が複数回送信された場合でも、ユーザーのクレジットが二重付与されず、べき等に処理されること。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_critical_invariants.py -v
  ```

---

### Step 12: CI パイプライン更新とローカル・CI 双方での ALL GREEN 最終検証
- **対象ファイル**:
  - [.github/workflows/ci.yml](file:///e:/hhh/.github/workflows/ci.yml)
- **作業内容**:
  1. GitHub Actions のワークフローで全ユニットテストおよびリグレッションテストが自動実行される設定を確認・調整。
  2. ローカル環境で全テストを一括実行し、エラー 0・失敗 0（ALL GREEN: 100% PASS）を確認。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/ -q
  ```
  *(出力末尾が `X passed, 0 failed, 0 error` となることを確認)*

---

## 3. 完了の定義 (Definition of Done)
1. [fail_now.txt](file:///e:/hhh/fail_now.txt) に記録されていた 45 件の失敗・11 件のエラーが 0 件になる。
2. 新設された 2 つのリグレッション防止テストスイート（`test_v5_pipeline_integrity.py`, `test_v5_critical_invariants.py`）が常時合格する。
3. `pytest` を単体実行した際、設定エラーやインポートエラーなく全テストが完走する。
