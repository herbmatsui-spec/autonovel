# コードレビュー改善 実装計画書（48マイクロステップ版）

**作成日**: 2026-08-16
**目的**: コードレビューの指摘を、**低性能 LLM でも迷わず 1 ステップずつ確実に** 完了できるよう、各フェーズを 12 の最小ステップに分割
**使い方**: 各ステップは「対象ファイル」「作業内容」「完了判定」のみ。1 ステップ = 1 つの PR または 1 コミットを想定。前のステップが通ってから次へ。

**共通ルール**:
- 編集前に必ず対象ファイルを `read` すること
- 編集後は必ず「完了判定」のコマンドを実行すること
- テストが壊れたらそのステップで止めて修正する

---

## Phase 0 — テスト修復・CI 緑化（P0）

### 0-1: archive インポートを含むテストファイルを列挙
- **対象**: `tests/` 配下
- **作業**: `grep -rn "from archive\." tests/` を実行し、該当ファイル名をメモ
- **完了判定**: 該当ファイルが `tests/unit/test_connection_kernel.py`, `tests/unit/test_commercial_roles.py`, `tests/test_narrative_engineering.py`, `tests/state/test_interaction_manager.py`, `tests/state/test_interaction_simulation.py` の 5 件であることを確認

### 0-2: test_connection_kernel.py を削除
- **対象**: `tests/unit/test_connection_kernel.py`
- **作業**: `git rm tests/unit/test_connection_kernel.py`
- **完了判定**: ファイルが存在しない（`ls tests/unit/test_connection_kernel.py` が No such file）

### 0-3: test_commercial_roles.py を削除
- **対象**: `tests/unit/test_commercial_roles.py`
- **作業**: `git rm tests/unit/test_commercial_roles.py`
- **完了判定**: ファイルが存在しない

### 0-4: test_narrative_engineering.py を削除
- **対象**: `tests/test_narrative_engineering.py`
- **作業**: `git rm tests/test_narrative_engineering.py`
- **完了判定**: ファイルが存在しない

### 0-5: tests/state/test_interaction_manager.py を削除
- **対象**: `tests/state/test_interaction_manager.py`
- **作業**: `git rm tests/state/test_interaction_manager.py`
- **完了判定**: ファイルが存在しない

### 0-6: tests/state/test_interaction_simulation.py を削除
- **対象**: `tests/state/test_interaction_simulation.py`
- **作業**: `git rm tests/state/test_interaction_simulation.py`
- **完了判定**: ファイルが存在しない

### 0-7: test_api_integration.py の import を修正
- **対象**: `tests/test_api_integration.py` 行 4
- **作業**: 行 4 `from httpx import AsyncClient` の下に追加:
  ```python
  from starlette.testclient import ASGITransport
  ```
- **完了判定**: ファイル先頭に `from starlette.testclient import ASGITransport` がある

### 0-8: test_api_integration.py の 4 箇所の AsyncClient を修正
- **対象**: `tests/test_api_integration.py` 行 22, 32, 43, 53
- **作業**: 4 箇所とも `async with AsyncClient(app=app, base_url="http://test") as client:` を `async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:` に置換
- **完了判定**: `grep -n "AsyncClient(app=app" tests/test_api_integration.py` が 0 件

### 0-9: tests/integration/conftest.py の import を修正
- **対象**: `tests/integration/conftest.py` 行 8-10
- **作業**: `from testcontainers.postgres import PostgresContainer` → `from testcontainers.community.postgres import PostgresContainer`（redis, generic も同様）
- **完了判定**: `grep -n "from testcontainers\." tests/integration/conftest.py` の結果がすべて `testcontainers.community.` 始まり

### 0-10: テストコレクション全体を確認
- **対象**: リポジトリ全体
- **作業**: `pytest tests/ --collect-only -q 2>&1 | tail -5`
- **完了判定**: `errors` が 0 件（`X tests collected, 0 errors`）

### 0-11: 修正した API 統合テストを実行
- **対象**: `tests/test_api_integration.py`
- **作業**: `pytest tests/test_api_integration.py -v 2>&1 | tail -10`
- **完了判定**: 4 件すべて passed（FAILED 0）

### 0-12: インテグレーションテスト収集を確認
- **対象**: `tests/integration/`
- **作業**: `pytest tests/integration --collect-only -q 2>&1 | tail -5`
- **完了判定**: `ImportError` / `ERROR` が 0 件

---

## Phase 1 — 構造整理・セキュリティ（P1）

### 1-1: 実態の alembic を特定
- **対象**: `alembic/versions/`, `src/backend/alembic/versions/`
- **作業**: 両ディレクトリのファイル数と最新マイグレーション名を比較（`ls alembic/versions/`, `ls src/backend/alembic/versions/`）
- **完了判定**: `src/backend/alembic/versions/` が 20+ ファイルで実態と判断できる

### 1-2: ルート alembic/ を削除
- **対象**: `alembic/`
- **作業**: `git rm -r alembic/`
- **完了判定**: `alembic/versions/` が存在しない

### 1-3: alembic.ini の script_location を修正
- **対象**: `alembic.ini`
- **作業**: `script_location = alembic` を `script_location = src/backend/alembic` に変更
- **完了判定**: `grep script_location alembic.ini` が `src/backend/alembic` を含む

### 1-4: src/services の参照元を列挙
- **対象**: `src/`
- **作業**: `grep -rn "from src.services" src/backend/routers src/core/container` を実行し、参照されているモジュールをメモ
- **完了判定**: どの `src/services/*` が使われているかリスト化済み

### 1-5: 未使用の src/services ファイルを archive へ移動
- **対象**: `src/services/`（1-4 で「未使用」と判定したファイル）
- **作業**: `git mv src/services/<unused>.py archive/services_legacy/<unused>.py`
- **完了判定**: 移動後に `grep -rn "from src.services.<unused>" src/` が 0 件

### 1-6: ルート計画書を docs/ へ移動
- **対象**: `IMPLEMENTATION_PLAN_*.md`, `CODE_REVIEW_*.md`, `48step_plan_jp.md` 等（ルートの .md 計画書）
- **作業**: 現在有効なもの（例: `IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md`）を `docs/` へ、`git mv`。過去のものを `archive/plans/` へ
- **完了判定**: ルート直下に `IMPLEMENTATION_PLAN_` または `CODE_REVIEW_` で始まるファイルが 0 件

### 1-7: streamlit_app を archive へ移動
- **対象**: `streamlit_app/`
- **作業**: `git mv streamlit_app archive/streamlit_retired_v2`
- **完了判定**: `streamlit_app/` が存在しない

### 1-8: RedisRateLimiter クラスを新規作成
- **対象**: `src/backend/rate_limit.py`（新規ファイル）
- **作業**: Redis ベースの sliding window レートリミッターを実装（既存 `src/services/redis_cache.py` の `RedisCacheService` を利用）
  ```python
  class RedisRateLimiter:
      def __init__(self, redis, max_requests: int, window: int): ...
      async def is_allowed(self, key: str) -> bool: ...
  ```
- **完了判定**: ファイルが作成され、`python -c "import src.backend.rate_limit"` でエラーなし

### 1-9: server.py のレート制限を Redis に置換
- **対象**: `src/backend/server.py:197-234`
- **作業**: `rate_limit_middleware` 内の `defaultdict` + `asyncio.Lock` ロジックを 1-8 の `RedisRateLimiter` 呼び出しに置換
- **完了判定**: `grep -n "_rate_limit_store" src/backend/server.py` が 0 件（Redis 化完了）

### 1-10: フロントエンドの exportPackage URL から api_key を除去
- **対象**: `frontend/src/api.ts:228-229`（`getExportPackageUrl`）
- **作業**: `?api_key=${encodeURIComponent(apiKey)}` を削除。apiKey 引数を関数シグネチャから外す
- **完了判定**: `grep -n "api_key=\${" frontend/src/api.ts` が 0 件

### 1-11: フロントエンドの exportPackage 関数から api_key を除去
- **対象**: `frontend/src/api.ts:302-307`（`exportPackage`）
- **作業**: `body: JSON.stringify({ api_key: apiKey })` を削除し、ヘッダ `Authorization: Bearer` または `X-API-Key` で渡すよう `apiRequest` 呼び出しを修正
- **完了判定**: `grep -n "api_key: apiKey" frontend/src/api.ts` が 0 件

### 1-12: CORS ヘッダを具体化
- **対象**: `src/backend/server.py:240-246`（`configure_cors`）
- **作業**: `allow_methods=["*"]` → `["GET","POST","PUT","DELETE","PATCH"]`、`allow_headers=["*"]` → `["Authorization","Content-Type","X-Trace-ID"]`
- **完了判定**: `grep -n 'allow_headers=\["\*"\]\|allow_methods=\["\*"\]\|allow_headers=\["\\*"\]' src/backend/server.py` が 0 件

---

## Phase 2 — 品質深化（P2）

### 2-1: mypy エラー数のベースライン計測
- **対象**: `pyproject.toml`（mypy セクション）
- **作業**: `mypy --config-file pyproject.toml src/ 2>&1 | grep -c "error:"` で現在数を記録（目標: 1769 → 880 以下）
- **完了判定**: 数値をメモ済み

### 2-2: LLMGenerateResultProxy の戻り値型を厳密化
- **対象**: `src/core/llm_gateway.py:146-259`
- **作業**: `generate_json` / `generate_text` の `**kwargs: Any` を削除し、戻り値を `GenerateResult` に固定（オーバーロード実装も合わせる）
- **完了判定**: 該当メソッドに `**kwargs: Any` が 0 件

### 2-3: engine._legacy を TypedDict で制約
- **対象**: `src/backend/engine.py:63,100-112`
- **作業**: `class _LegacyDeps(TypedDict): planner: ...` を定義し、`self._legacy: _LegacyDeps` に型付け（後方互換維持）
- **完了判定**: `self._legacy: Any` が `self._legacy: _LegacyDeps` になっている

### 2-4: EngineFacade の存在確認
- **対象**: `src/backend/engine_facade.py`
- **作業**: ファイルを `read` し、HTTP/DB/タスク管理の責務が Facade にあるか確認
- **完了判定**: Facade の責務範囲をメモ済み

### 2-5: エンジンから Facade へ責務を 1 つ移動
- **対象**: `src/backend/engine.py`, `src/backend/engine_facade.py`
- **作業**: エンジンが直接持つ「オーケストレーション系」メソッドのうち最も簡単な 1 つ（例: `sync_bible`）を Facade に委譲し、エンジンは呼び出しのみにする
- **完了判定**: 移動したメソッドがエンジンから削除（または薄いラッパーに）

### 2-6: E2E テスト雛形を作成
- **対象**: `frontend/e2e/`（`easy-mode.spec.ts` 新規）
- **作業**: Playwright の `test()` 雛形を書く（実装は空で `todo` のみ）。`frontend/playwright.config.ts` が `e2e/` を指すか確認
- **完了判定**: `frontend/e2e/easy-mode.spec.ts` が存在し、`npx playwright test --list` で認識される

### 2-7: E2E: かんたんモード生成フローを実装
- **対象**: `frontend/e2e/easy-mode.spec.ts`
- **作業**: 「ジャンル選択 → 生成ボタン → 結果表示」のステップを `getByRole` / `click` / `waitFor` で記述
- **完了判定**: テストがローカルで実行可能（`npx playwright test e2e/easy-mode.spec.ts` が少なくとも収集される）

### 2-8: SpiceGuard 日本語境界判定を改善
- **対象**: `src/easy_mode/spice_guard/extractor.py:171-191`
- **作業**: `_is_word_boundary` で `unicodedata.category(ch)` を用い、日本語文字（Lo/Lt/Lm）を境界として扱うよう修正
- **完了判定**: `grep -n "'a' <= prev_char" src/easy_mode/spice_guard/extractor.py` が 0 件（ASCII 専用判定を削除）

### 2-9: プロンプトインジェクション対策を 1 ファイルへ適用
- **対象**: `src/easy_mode/bible_generator.py`
- **作業**: ユーザー入力（`concept` 等）をプロンプトに埋め込む箇所で Jinja2 `SandboxedEnvironment` または明示的エスケープを適用
- **完了判定**: 該当ファイルで `f"..."` 直接埋め込みが 0 件（エスケープ関数経由に）

### 2-10: bible_generator の単体テストを作成
- **対象**: `tests/unit/test_bible_generator.py`（新規）
- **作業**: モック LLM（`generate_json` をスタブ）で `BibleGenerator.generate()` を呼び、戻り値の型・必須キーを検証
- **完了判定**: `pytest tests/unit/test_bible_generator.py -v` が passed

### 2-11: spice_guard extractor の単体テストを作成
- **対象**: `tests/unit/test_spice_extractor.py`（新規）
- **作業**: 日本語混在テキストで `SpiceExtractor.extract()` を呼び、境界判定の正誤を検証（2-8 の修正をカバー）
- **完了判定**: `pytest tests/unit/test_spice_extractor.py -v` が passed

### 2-12: exceptions 階層の単体テストを作成
- **対象**: `tests/unit/test_exceptions.py`（新規）
- **作業**: `HegemonyError` サブクラスが正しい `status_code` / `error_code` を持つことを検証
- **完了判定**: `pytest tests/unit/test_exceptions.py -v` が passed

---

## Phase 3 — 高度化（P3）

### 3-1: mutmut を dev 依存に追加
- **対象**: `requirements.txt`（DEV/CI セクション）
- **作業**: `mutmut>=2.0.0` を追加
- **完了判定**: `grep mutmut requirements.txt` が該当行を返す

### 3-2: mutmut 設定ファイルを作成
- **対象**: `mutmut_config.py`（新規）または `pyproject.toml` の `[tool.mutmut]`
- **作業**: 対象パスを `src/easy_mode/`, `src/core/` に設定、`src/backend/server.py` 等を除外
- **完了判定**: `mutmut list` がエラーなく実行される

### 3-3: 1 モジュールで mutmut を試験実行
- **対象**: `src/easy_mode/models.py`
- **作業**: `mutmut run --paths-to-mutate src/easy_mode/models.py` を実行し、生存率を確認
- **完了判定**: 実行ログに生存率（% ）が出力される

### 3-4: バックエンド OpenAPI スキーマを出力
- **対象**: `src/backend/server.py`
- **作業**: 起動後 `curl localhost:8200/openapi.json > docs/openapi.json` または `app.openapi()` で JSON 出力
- **完了判定**: `docs/openapi.json` が存在し、有効な JSON

### 3-5: フロントエンド型定義との整合スクリプト
- **対象**: `frontend/src/types/api.ts`
- **作業**: OpenAPI → TypeScript 型生成ツール（openapi-typescript 等）を選定し、package.json に `typegen` スクリプト追加
- **完了判定**: `package.json` の scripts に `typegen` がある

### 3-6: Dockerfile をマルチステージ化
- **対象**: `Dockerfile`
- **作業**: `FROM python:3.12-slim AS builder` で `pip install --user`、runtime ステージで `COPY --from=builder` に分割
- **完了判定**: `grep -n "AS builder" Dockerfile` が該当行を返す

### 3-7: Dockerfile に非 root ユーザーを追加
- **対象**: `Dockerfile`（runtime ステージ末尾）
- **作業**: `RUN useradd -m appuser && chown -R appuser /app` と `USER appuser` を追加
- **完了判定**: `grep -n "USER appuser" Dockerfile` が該当行を返す

### 3-8: frontend Dockerfile のステージ確認
- **対象**: `frontend/Dockerfile`
- **作業**: `docker-compose.yml` が参照する `target: dev` / `production` ステージが定義されているか `read` で確認。不足なら追加
- **完了判定**: `frontend/Dockerfile` に `FROM ... AS dev` と `AS production` がある

### 3-9: OpenTelemetry サンプリング率を環境別に
- **対象**: `src/core/opentelemetry.py`
- **作業**: `setup_opentelemetry` の `sample_rate` を環境変数（develop=1.0, production=0.1）から取得するよう修正
- **完了判定**: `grep -n "sample_rate" src/core/opentelemetry.py` が環境変数参照になっている

### 3-10: ビジネス KPI メトリクスを追加
- **対象**: `src/backend/observability/metrics.py`
- **作業**: `kaku_pipeline_episodes_total`, `kaku_pipeline_avg_audit_score`, `kaku_pipeline_cost_usd` 等の Counter/Gauge を追加
- **完了判定**: 新メトリクス名が `kaku_` 規約に従っている

### 3-11: limit_concurrency セマフォをインスタンス変数化
- **対象**: `src/core/async_utils.py`, `src/easy_mode/pipeline.py:110,124`
- **作業**: パイプライン初期化時に 1 つの `asyncio.Semaphore` を作成し、各話生成で再利用（毎回新規作成をやめる）
- **完了判定**: `grep -n "limit_concurrency(" src/easy_mode/pipeline.py` の呼び出しがセマフォ引数を受け取る形になっている

### 3-12: 長文生成のトークン制限・自動要約を追加
- **対象**: `src/easy_mode/episode_writer.py`
- **作業**: `config/settings.py` の `max_prompt_chars` を超える入力で、先頭/要約に切り詰めるヘルパーを追加（LLM 呼び出し前）
- **完了判定**: `max_prompt_chars` 超過時に例外ではなく要約処理される単体テストを追加

---

## 完了判定サマリー（全フェーズ共通）

| チェック | コマンド |
|----------|----------|
| テスト収集エラー 0 | `pytest tests/ --collect-only -q 2>&1 \| tail -3` |
| 単体/統合テスト通過 | `pytest tests/unit tests/integration -q 2>&1 \| tail -5` |
| Ruff 重大エラー 0 | `ruff check src/ tests/` |
| mypy strict（新規） | `mypy --config-file pyproject.toml src/<変更ファイル>` |
| セキュリティ | `bandit -r src/ config/ -ll` および `gitleaks detect` |
| 依存脆弱性 | `pip-audit -r requirements.txt` |

各ステップ完了ごとに上記の関連項目を実行し、赤ならそのステップ内で止めて修正すること。
