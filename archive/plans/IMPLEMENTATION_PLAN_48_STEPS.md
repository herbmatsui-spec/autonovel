# 48ステップ実装計画: 自動小説生成システムの品質向上・バグ修正・アーキテクチャ改善

## 概要
コードベース全体の精査により特定されたエラー、コンフリクト、矛盾点を解決し、低性能LLMでも実装可能な粒度（1ステップ≒1ファイル/1関数単位）に分解した実装計画。

---

## フェーズ 1: 緊急バグ修正（ステップ 1-8）

### ステップ 1: `PipelineError` 例外クラスの定義追加
**ファイル**: `src/core/exceptions.py`  
**内容**: `src/core/exceptions.py` に `PipelineError` クラスを追加（`HegemonyError` を継承）。`commercial_pipeline.py` が `from src.core.exceptions import PipelineError` でインポートできるようにする。
**検証**: `tests/test_commercial_pipeline_error.py` がパスすること。

### ステップ 2: `commercial_pipeline.py` のリトライデコレータのバグ修正
**ファイル**: `src/backend/workflows/commercial_pipeline.py`（行 34-36）  
**内容**: `jitter = delay * 0.1 * (await asyncio.sleep(0) or 1)` のバグを修正。`await asyncio.sleep(0)` は `None` を返すため常に `1` になる。正しくは `jitter = delay * 0.1 * random.uniform(0.5, 1.5)` 等のランダムジッターを使用。
**検証**: `tests/test_commercial_pipeline_unit.py::test_pipeline_retry_decorator_success` がパスすること。

### ステップ 3: `commercial_pipeline.py` に不足しているインポートの追加
**ファイル**: `src/backend/workflows/commercial_pipeline.py`  
**内容**: ファイル冒頭に `from typing import Optional, Dict, List, Any` を追加（現状 `Optional`, `Dict`, `List`, `Any` が未インポートで実行時エラーになる）。
**検証**: `python -c "from src.backend.workflows.commercial_pipeline import CommercialPipeline"` がエラーなく実行できること。

### ステップ 4: `_step_plan_async` メソッドの実装またはメソッド名の統一
**ファイル**: `src/backend/workflows/commercial_pipeline.py` / `tests/test_commercial_pipeline_error.py`  
**内容**: テストが `pipeline._step_plan_async()` を呼び出しているが、実装は `_step_plan`（同期メソッド）のみ。`_step_plan` を `async def _step_plan_async` にリネームし、非同期化するか、テスト側を `_step_plan` 呼び出しに修正。
**検証**: `tests/test_commercial_pipeline_error.py::test_step_plan_raises_pipeline_error` がパスすること。

### ステップ 5: `test_commercial_pipeline_unit.py` の不正なパッチ修正
**ファイル**: `tests/test_commercial_pipeline_unit.py`（行 72-77）  
**内容**: `with patch.object(pipeline, "run", new_value=PipelineError("Test error")):` は誤り。`new_value` で例外インスタンスを設定しても呼び出し時に例外は送出されない。`side_effect=PipelineError("Test error")` に修正。
**検証**: `tests/test_commercial_pipeline_unit.py::test_run_handles_pipeline_error_gracefully` がパスすること。

### ステップ 6: `CommercialConfig` とパイプラインのフィールド名統一
**ファイル**: `src/backend/routers/commercial.py` / `src/backend/workflows/commercial_pipeline.py`  
**内容**: ルーターの `CommercialConfig` は `target_word_count` を使用だが、パイプラインの `_step_plan` は `target_word_count_per_episode` を期待。どちらかに統一（推奨: `target_word_count_per_episode` に統一し、ルーター側でバリデーション追加）。
**検証**: `/api/commercial/run` に `target_word_count: 3000` を送信しても正しく `target_word_count_per_episode` として処理されること。

### ステップ 7: `_create_schedule_csv` のハードコードパス修正
**ファイル**: `src/backend/workflows/commercial_pipeline.py`（行 244）  
**内容**: `csv_path = "/tmp/commercial_schedule.csv"` を設定可能にする。`tempfile.mkstemp(suffix=".csv", prefix="commercial_schedule_")` または環境変数 `COMMERCIAL_SCHEDULE_DIR` を参照する実装に変更。
**検証**: 複数同時実行時に CSV パスが競合しないこと。テストで一時ディレクトリが使用されることを確認。

### ステップ 8: `EpisodeWriter.write` のダミー `book_id=0` 修正
**ファイル**: `src/backend/workflows/commercial_pipeline.py`（行 188）  
**内容**: `book_id=0` を渡している箇所を、実際の `book_id`（パイプライン実行時に作成される Bible/Book の ID）を使用するよう修正。`run` メソッドで Bible 作成→Book 作成→ID 取得→EpisodeWriter に渡すフローを実装。
**検証**: 実際の DB レコードと整合する `book_id` でエピソードが生成されること。

---

## フェーズ 2: 設定・アーキテクチャの統一（ステップ 9-16）

### ステップ 9: `config/base.py` （非推奨定数）の段階的削除計画策定
**ファイル**: `config/base.py` / `schemas/config.py` / `config/validator.py`  
**内容**: `config/base.py` の定数（`MODEL_PLANNING`, `DATABASE_URL`, `CATHARSIS_THRESHOLD` 等）が `schemas/config.py` の `GlobalConfigModel` と重複。移行ガイドを `docs/config_migration_guide.md` に作成し、参照箇所を `config.validator.ConfigValidator.load()` 経由に一本化する計画を文書化。
**検証**: 移行ガイドドキュメントが存在し、全参照箇所がリストアップされていること。

### ステップ 10: `config/validator.py` の `validate_all` 戻り値型の明確化
**ファイル**: `config/validator.py`（行 124-235）  
**内容**: `validate_all(strict=True) -> Dict[str, Any]` の戻り値に含まれるキー（`settings`, `models`, `plugins`, `tropes`, `interaction_matrix`, `domain_profiles`）を docstring で明記し、各値の型を `TypedDict` で定義。
**検証**: 型ヒントが mypy でパスすること。

### ステップ 11: `GlobalConfigModel.apply_env_overrides` の型安全性向上
**ファイル**: `schemas/config.py`（行 187-206）  
**内容**: `_coerce_env_value` で `annotation` が `Union` や `Optional` の場合のハンドリングを追加。`get_origin` / `get_args` を使用してネストした型にも対応。
**検証**: 環境変数 `MODEL_PLANNING=gemini-4` 設定時に正しく上書きされること。

### ステップ 12: 重複ファイル `streamlit_app/ui_tabs_writing.py` と `src/streamlit_app/ui_tabs_writing.py` の統合
**ファイル**: 両ファイル  
**内容**: 内容がほぼ同一。`streamlit_app/` 側を削除し、`src/streamlit_app/` を正式パスとする。`streamlit_app/landing.py` 等の import パスを `from src.streamlit_app.ui_tabs_writing import render_novel_production_tab` に統一。
**検証**: Streamlit アプリが `streamlit run streamlit_app/landing.py` で正常起動すること。

### ステップ 13: `config/container.py` DI コンテナの実装完成
**ファイル**: `config/container.py`  
**内容**: 現状 `Container` クラスが空。`providers.Configuration()`, `providers.Singleton()`, `providers.Factory()` で主要サービス（`EpisodeWriter`, `NovelProducer`, `LLMClient`, `DatabaseManager` 等）を登録。
**検証**: `python -c "from config.container import Container; c = Container(); c.wire(modules=['src.backend.routers.novel'])"` がエラーなく実行できること。

### ステップ 14: `src/backend/engine.py` `UltimateHegemonyEngine` の DI 対応
**ファイル**: `src/backend/engine.py` / `config/container.py`  
**内容**: `UltimateHegemonyEngine.__init__` が直接インスタンスを生成している箇所を、DI コンテナから注入されるプロバイダ経由に変更。
**検証**: ルーター経由でエンドポイント呼び出し時にエンジンが正しく初期化されること。

### ステップ 15: `src/backend/background.py` `ProgressState` の Redis キー命名規則統一
**ファイル**: `src/backend/background.py`  
**内容**: `_save_to_db` で使用する Redis キー（`f"progress:{self.task_id}"`）と、`src/backend/routers/tasks.py` で使用するキーが一致することを確認・統一。`task:{task_id}:progress` 形式に標準化。
**検証**: `/api/tasks/{id}/status` と `/api/tasks/{id}/stream` が同じ進捗データを返すこと。

### ステップ 16: `src/backend/engine_context.py` `ContextManager` の非同期メソッド統一
**ファイル**: `src/backend/engine_context.py`  
**内容**: `build_past_context`, `get_optimal_context`, `get_optimal_context_split`, `get_structured_context_split` がすべて `async def` だが、内部で同期的な DB 呼び出し（`repo.get_*`）を行っている。非同期リポジトリ（`async with db.get_session()`）に統一、または `run_in_executor` でラップ。
**検証**: 並行リクエスト時にイベントループがブロックされないこと。

---

## フェーズ 3: 商用パイプライン機能強化（ステップ 17-28）

### ステップ 17: 商用パイプラインのタスクステータス連携実装
**ファイル**: `src/backend/workflows/commercial_pipeline.py` / `src/backend/background.py` / `src/backend/routers/tasks.py`  
**内容**: `CommercialPipeline.run()` 内で `ProgressState` / `BackgroundReporter` を使用し、各ステップ（plan, bible, content, csv）で進捗を Redis に保存。`/api/tasks/{id}/status` で取得可能にする。
**検証**: E2E テスト `test_commercial_pipeline_end_to_end` のポーリングが正常に進捗を取得できること。

### ステップ 18: `run_commercial_pipeline` エンドポイントの非同期タスク化
**ファイル**: `src/backend/routers/commercial.py`  
**内容**: 現状同期的に `pipeline.run()` を待機している。`BackgroundTasks` または Huey/Redis Queue を使用してバックグラウンド実行し、即座に `task_id` を返却する方式に変更。
**検証**: POST `/api/commercial/run` が 202 Accepted + `task_id` を即座に返すこと。

### ステップ 19: `CommercialConfig` Pydantic モデルのバリデーション強化
**ファイル**: `src/backend/routers/commercial.py`  
**内容**: `series_config` に `target_eps` (1-100), `target_word_count_per_episode` (500-10000), `genre` (enum), `keywords` (min_items=1) 等のバリデーション追加。
**検証**: 不正なリクエストで 422 が返ること。正常リクエストでパイプラインが起動すること。

### ステップ 20: Bible 生成ステップの実装（モックから実装へ）
**ファイル**: `src/backend/workflows/commercial_pipeline.py`（`_step_plan` 内）  
**内容**: 現状 `_step_plan` は Bible 構造をモックで返している。`src/agents/bible.py` の `BibleAgent` を使用して実際に Bible を生成・DB 保存する実装に置き換え。
**検証**: 生成された Bible が `bibles` テーブルに保存され、`run` 戻り値の `data.bible` に含まれること。

### ステップ 21: エピソード生成の並列化・バッチ処理対応
**ファイル**: `src/backend/workflows/commercial_pipeline.py`（`_generate_content`）  
**内容**: 現在シーケンシャルに `for ep_num in range(1, target_eps+1)` で生成。`asyncio.gather` + `semaphore` で並列度制御（`MAX_CONCURRENCY` 設定値）しつつバッチ生成する実装に変更。
**検証**: 10話生成時に並列実行され、所要時間が短縮されること。

### ステップ 22: CSV スケジュール生成のカスタマイズ可能化
**ファイル**: `src/backend/workflows/commercial_pipeline.py`（`_create_schedule_csv`）  
**内容**: 出力カラム（掲載日、タイトル、文字数、タグ等）を `SeriesConfig` または環境変数でカスタマイズ可能に。デフォルトは Kakuyomu/Narou 形式。
**検証**: 設定変更時に CSV ヘッダーが変わること。

### ステップ 23: エピソード品質チェック・自動リライト機能の追加
**ファイル**: `src/backend/workflows/commercial_pipeline.py` / `src/agents/writing.py`  
**内容**: 生成後に `EarlyEntertainmentChecker` / `EroticIntegrityChecker` 等で品質スコア計算。閾値未満なら `ActorCriticLoop` でリライト（最大 2 回）。
**検証**: 品質スコア閾値未満のエピソードが自動リライトされ、スコア向上すること。

### ステップ 24: 商用パイプラインのエラー分類とリトライ戦略の詳細化
**ファイル**: `src/backend/workflows/commercial_pipeline.py` / `src/core/exceptions.py`  
**内容**: `LLMTemporaryError` (RateLimit, Timeout), `LLMUnrecoverableError` (InvalidRequest, ContextLength) 等で分類。`async_retry` デコレータに `retry_on` 引数を追加し、エラー種別ごとにリトライ可否を制御。
**検証**: RateLimit エラー時はリトライ、InvalidRequest 時は即座に失敗すること。

### ステップ 25: マルチプラットフォーム対応（カクヨム/小説家になろう/カクヨムコンテスト等）
**ファイル**: `src/backend/workflows/commercial_pipeline.py` / `prompts/commercial_prompts.py`  
**内容**: `platforms` 配列に応じて、Bible の `target_platforms`、文体 DNA、マーケティングフック、CSV 出力フォーマットを切り替え。
**検証**: `platforms: ["kakuyomu", "naru", "kakuyomu_contest"]` 指定時に各プラットフォーム向け出力が生成されること。

### ステップ 26: シリーズ展開・スピンオフ自動企画機能の統合
**ファイル**: `prompts/commercial_prompts.py`（`SERIES_EXPENSION_PROMPTS`） / `src/backend/workflows/commercial_pipeline.py`  
**内容**: パイプライン完了後、生成された Bible/エピソードからシリーズ展開案・スピンオフ案を自動生成し、レポートに含める。
**検証**: パイプライン完了レスポンスに `series_expansion` キーが含まれること。

### ステップ 27: A/B テスト用プロンプトバリアント自動生成の統合
**ファイル**: `prompts/commercial_prompts.py`（`AB_TEST_PROMPTS`） / `src/backend/workflows/commercial_pipeline.py`  
**内容**: 同一設定で複数の文体・フックバリエーションを生成し、品質スコア比較レポートを出力。
**検証**: `platforms` に `ab_test` を含めると複数バリエーションが生成されること。

### ステップ 28: 商用パイプライン実行ログの構造化・監査証跡化
**ファイル**: `src/backend/workflows/commercial_pipeline.py` / `src/backend/database/models.py`（`AuditIssue`）  
**内容**: 各ステップの入力・出力・LLM 呼び出し回数・トークン数・コスト・実行時間を `audit_issues` または専用テーブル `commercial_pipeline_runs` に記録。
**検証**: 実行後に DB から監査ログを取得し、再現可能な情報が揃っていること。

---

## フェーズ 4: Streamlit UI 改善・重複排除（ステップ 29-36）

### ステップ 29: 重複 UI ファイルの削除と import 統一
**ファイル**: `streamlit_app/ui_tabs_writing.py` (削除) / `src/streamlit_app/ui_tabs_writing.py` (正式)  
**内容**: `streamlit_app/landing.py`, `streamlit_app/progress.py` 等の import を `from src.streamlit_app.ui_tabs_writing import render_novel_production_tab` に統一。
**検証**: `streamlit run streamlit_app/landing.py` でエラーなく起動すること。

### ステップ 30: Streamlit 側のリトライデコレータの非同期対応
**ファイル**: `src/streamlit_app/ui_tabs_writing.py`（`retry_api` デコレータ）  
**内容**: 現状同期的な `time.sleep` を使用。Streamlit はシングルスレッドのためブロッキングになる。`asyncio.sleep` + `st.experimental_rerun` または `st.empty()` による非ブロッキング待機に変更。
**検証**: API 呼び出し失敗時に UI がフリーズせず、リトライ待機中も他の操作が可能であること。

### ステップ 31: ポーリング処理の非同期化・バックグラウンドタスク化
**ファイル**: `src/streamlit_app/ui_tabs_writing.py`（行 174-237）  
**内容**: `while elapsed < max_wait_seconds:` ループで `time.sleep` しつつ `httpx.get` している。`asyncio.create_task` でバックグラウンドポーリングし、`st.session_state` に結果を格納。UI は `st.rerun()` で進捗表示を更新。
**検証**: ポーリング中も UI の他ボタン（停止、キャンセル等）が反応すること。

### ステップ 32: ハードコードされた API エンドポイントの環境変数化
**ファイル**: `src/streamlit_app/ui_tabs_writing.py`（行 100, 186, 203, 277, 299）  
**内容**: `http://localhost:8000` を `os.environ.get("BACKEND_API_URL", "http://localhost:8000")` に置換。`.streamlit/secrets.toml` または環境変数で設定可能に。
**検証**: 異なるホスト・ポートのバックエンドに接続できること。

### ステップ 33: プロジェクト ID（book_id）の動的取得対応
**ファイル**: `src/streamlit_app/ui_tabs_writing.py`（行 203）  
**内容**: `http://localhost:8000/api/novel/1/report` の `1` をハードコード。パイプライン実行時に返却される `book_id` または `project_id` を `st.session_state` に保存し、レポート取得時に使用。
**検証**: 複数プロジェクト連続実行時に正しいレポートが取得されること。

### ステップ 34: CSV ダウンロード機能のメモリ効率化
**ファイル**: `src/streamlit_app/ui_tabs_writing.py`（行 163-168）  
**内容**: `with open(csv_path, "rb") as f: st.download_button(data=f.read())` はファイル全体をメモリに読み込む。`data=csv_path` (pathlib.Path) またはジェネレータ関数を渡してストリーミングダウンロードに対応。
**検証**: 大きな CSV（100MB 以上）でもメモリ枯渇せずダウンロードできること。

### ステップ 35: エラーハンドリングの統一・ユーザーフレンドリー化
**ファイル**: `src/streamlit_app/ui_tabs_writing.py`  
**内容**: `st.error(f"通信エラー: {e}")` 等を共通関数 `handle_api_error(e: Exception, context: str)` に集約。エラー種別（ネットワーク、4xx、5xx、タイムアウト）ごとに適切なメッセージ・リトライボタンを表示。
**検証**: 各種エラーシミュレーションで適切な UI が表示されること。

### ステップ 36: セッションステート管理の型安全化・初期化集約
**ファイル**: `src/streamlit_app/ui_tabs_writing.py`（行 14-21）  
**内容**: `st.session_state` キーを `CommercialSessionState` という `TypedDict` または `dataclass` で定義。初期化を `init_session_state()` 関数に集約し、ページ読み込み時に一度だけ呼び出す。
**検証**: キーの typo によるバグが型チェックで検出されること。

---

## フェーズ 5: テスト拡充・品質保証（ステップ 37-42）

### ステップ 37: 商用パイプライン統合テストのフィクスチャ整備
**ファイル**: `tests/conftest.py` (新規) / `tests/test_commercial_end_to_end.py`  
**内容**: `pytest-asyncio`, `httpx.AsyncClient`, テスト用 SQLite DB (`:memory:`), テスト用 Redis (fakeredis) のフィクスチャを `conftest.py` に定義。E2E テストが独立して実行可能に。
**検証**: `pytest tests/test_commercial_end_to_end.py -v` が単体でパスすること。

### ステップ 38: 単体テストのモック戦略統一
**ファイル**: `tests/test_commercial_pipeline_unit.py` / `tests/test_commercial_pipeline_error.py`  
**内容**: `unittest.mock.patch` の使用を `pytest-mock` の `mocker` fixture に統一。`AsyncMock` を適切に使用し、非同期メソッドのモックを正しく行う。
**検証**: 全単体テストが `pytest tests/test_commercial_pipeline_*.py -v` でパスすること。

### ステップ 39: エピソードライターのエッジケーステスト追加
**ファイル**: `tests/test_episode_writer.py` (新規)  
**内容**: `EpisodeWriter.write` のテスト: ① WritingAgent 正常、② WritingAgent 例外→フォールバック、③ WritingAgent 未インストール→フォールバック、④ 文字数指定・前話コンテキスト反映の検証。
**検証**: 新規テストファイルがパスし、カバレッジが 80% 以上。

### ステップ 40: NovelProducer の全話生成フローテスト追加
**ファイル**: `tests/test_novel_producer.py` (新規)  
**内容**: `NovelProducer.generate_all_episodes` のテスト: 正常完了、中間失敗時の進捗ステータス更新、トークン使用量集計、レポート生成の検証。
**検証**: 新規テストファイルがパスすること。

### ステップ 41: 設定バリデーションテストの追加
**ファイル**: `tests/test_config_validator.py` (新規)  
**内容**: `ConfigValidator.validate_all` のテスト: 正常系、必須ファイル欠落時のデフォルト値適用、不正な値での `strict=True` 時の例外送出、環境変数上書きの動作確認。
**検証**: 新規テストファイルがパスすること。

### ステップ 42: CI パイプラインへのテスト統合
**ファイル**: `.github/workflows/ci.yml` (新規または更新) / `pyproject.toml`  
**内容**: `pytest --cov=src --cov-fail-under=70`, `mypy src`, `ruff check src` を GitHub Actions で実行。テスト並列化 (`pytest-xdist`) で高速化。
**検証**: PR 作成時に CI が自動実行され、カバレッジ・型チェック・リンターがパスすること。

---

## フェーズ 6: ドキュメント・運用・リファクタリング（ステップ 43-48）

### ステップ 43: 設定移行ガイドの作成
**ファイル**: `docs/config_migration_guide.md` (新規)  
**内容**: `config/base.py` 定数から `schemas/config.py` + `config/settings.toml` への移行手順、環境変数マッピング表、既存コードの書き換え例を文書化。
**検証**: ドキュメントに従って移行作業が完了できること。

### ステップ 44: API 仕様書（OpenAPI）の自動生成・公開設定
**ファイル**: `src/backend/server.py` / `docs/api_spec.md`  
**内容**: FastAPI の `app.openapi()` を利用し、ビルド時に `openapi.json` を生成。`docs/api_spec.md` に Redoc/ Swagger UI へのリンクを記載。`/docs` エンドポイントで Swagger UI を公開。
**検証**: `http://localhost:8000/docs` で API ドキュメントが閲覧できること。

### ステップ 45: デプロイメントガイドの更新・K8s マニフェストの検証
**ファイル**: `docs/deployment_guide.md` / `deploy_scripts/deploy.sh` / `k8s/*.yaml`  
**内容**: 環境変数一覧（`DATABASE_URL`, `REDIS_URL`, `BACKEND_API_URL`, `MODEL_*` 等）を網羅。Helm chart への移行検討事項を追記。`deploy.sh` のレジストリ・タグ・名前空間をパラメータ化。
**検証**: ガイドに従って `kubectl apply -f k8s/` で全リソースが正常作成されること。

### ステップ 46: ログ・メトリクス・トレーシングの標準化
**ファイル**: `config/logging_config.py` / `src/backend/engine.py` / `services/tracing_service.py`  
**内容**: 構造化ログ（JSON）、OpenTelemetry トレーシング（`services/tracing_service.py` 既存）、Prometheus メトリクス（`/metrics` エンドポイント）を全サービスで有効化。相関 ID (`trace_id`) をリクエストヘッダー・ログ・DB に伝播。
**検証**: Grafana/Loki でログ検索、Jaeger でトレース確認、Prometheus でメトリクス取得が可能であること。

### ステップ 47: パフォーマンスベンチマーク・負荷テストスクリプトの整備
**ファイル**: `scripts/load_test.py` (新規) / `docs/benchmark_results.md`  
**内容**: `locust` または `hey` を使用した負荷テストシナリオ: ① `/api/commercial/run` 同時 10 リクエスト、② `/api/tasks/{id}/status` ポーリング 100 並列。ボトルネック（DB 接続プール、Redis、LLM API レートリミット）を特定し、チューニングパラメータを文書化。
**検証**: ベンチマーク実行時にエラー率 < 1%、P99 レイテンシ < 5s を達成すること。

### ステップ 48: 技術的負債解消・リファクタリングバックログの整理
**ファイル**: `TECH_DEBT.md` (新規) / `pyproject.toml` (`[tool.ruff.lint]` 設定追加)  
**内容**: 
- 循環インポートの解消 (`src/agents/writing.py` ↔ `src/services/episode_writer.py` 等)
- `config/base.py` 定数の完全削除スケジュール
- 型ヒント不足箇所の補完 (`mypy --strict` 対応)
- 非推奨 `typing.Union` → `X | Y` 移行
- テストカバレッジ 80% 達成計画
- 依存関係の更新・脆弱性スキャン (`pip-audit`, `dependabot`)
**検証**: `TECH_DEBT.md` が優先度付きで整理され、マイルストーンごとに消化計画があること。

---

## 実装優先度マトリクス

| 優先度 | ステップ | 理由 |
|--------|----------|------|
| **P0 (即時)** | 1-8 | 実行時エラー・テスト失敗の直接原因 |
| **P1 (高)** | 9-16 | アーキテクチャの一貫性・保守性に直結 |
| **P2 (中)** | 17-28 | 商用パイプラインの本番運用に必要な機能 |
| **P3 (中)** | 29-36 | UI/UX・開発体験の改善 |
| **P4 (低)** | 37-42 | 品質保証基盤の整備 |
| **P5 (継続)** | 43-48 | ドキュメント・運用・長期保守性 |

---

## 進捗管理テンプレート

```markdown
## 進捗サマリ (更新日: YYYY-MM-DD)

| フェーズ | 総ステップ | 完了 | 進行中 | 未着手 | ブロック |
|----------|------------|------|--------|--------|----------|
| 1: 緊急バグ修正 | 8 | 0 | 0 | 8 | 0 |
| 2: 設定・アーキテクチャ統一 | 8 | 0 | 0 | 8 | 0 |
| 3: 商用パイプライン強化 | 12 | 0 | 0 | 12 | 0 |
| 4: Streamlit UI 改善 | 8 | 0 | 0 | 8 | 0 |
| 5: テスト拡充 | 6 | 0 | 0 | 6 | 0 |
| 6: ドキュメント・運用 | 6 | 0 | 0 | 6 | 0 |
| **合計** | **48** | **0** | **0** | **48** | **0** |

### 今週のフォーカス (Week 1)
- [ ] ステップ 1: PipelineError 定義
- [ ] ステップ 2: リトライデコレータ修正
- [ ] ステップ 3: 不足インポート追加
- [ ] ステップ 4: _step_plan_async 実装
- [ ] ステップ 5: テストパッチ修正

### ブロッカー
- なし（現時点）
```

---

## 付録: 主要ファイルマップ

| カテゴリ | ファイル | 役割 |
|----------|----------|------|
| **商用パイプライン** | `src/backend/workflows/commercial_pipeline.py` | コアパイプライン実装 |
| | `src/backend/routers/commercial.py` | API エンドポイント |
| | `tests/test_commercial_*.py` | テスト群 |
| **設定管理** | `schemas/config.py` | SSOT (GlobalConfigModel) |
| | `config/validator.py` | 設定読み込み・検証 |
| | `config/base.py` | 非推奨定数 (移行対象) |
| **サービス層** | `src/services/novel_producer.py` | 制作オーケストレーション |
| | `src/services/episode_writer.py` | エピソード執筆委譲 |
| | `src/agents/writing.py` | Writing Agent 実装 |
| **データ層** | `src/backend/database/models.py` | SQLAlchemy ORM |
| | `src/models/db.py` | Pydantic DB モデル |
| **UI** | `src/streamlit_app/ui_tabs_writing.py` | Streamlit 小説生成タブ |
| **インフラ** | `deploy_scripts/deploy.sh` | デプロイ自動化 |
| | `docs/deployment_guide.md` | K8s/Docker 手順 |
| **プロンプト** | `prompts/commercial_prompts.py` | 商用プロンプトレジストリ |

---

**作成日**: 2026-07-13  
**対象バージョン**: autonovel main branch (commit: latest)  
**想定工数**: 約 48-60 人日 (1ステップ平均 1-1.5 人日)  
**推奨体制**: 2-3 名並列 (バグ修正・機能・UI/テストで分担)