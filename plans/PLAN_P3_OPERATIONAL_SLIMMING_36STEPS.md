# AutoNovel 実装計画書: Phase 3 (P3)
# 運用のスリム化とコア機能フォーカス (36 Steps)

**目的**: Windows環境での1クリックローカル起動の完全修復（READMEの「非推奨」汚名返上）、Docker設定の軽量化、重厚なマルチメディア機能のプラグイン疎結合化、ドキュメントの真実性回復を行い、実用性の高いクリーンな出版支援エンジンを完成させる。  
**対象読者**: 小型・低性能LLM（Small LLM / 7Bクラス等）でも迷わず1ステップずつ順次実行できるように、ファイルパス、修正内容、テストケース名、検証コマンドを厳密に定義。

---

## 📋 全体構成（36ステップ）

- **Part 1 (Step 1-8)**: ローカル起動スクリプトの完全修復と安定化
- **Part 2 (Step 9-14)**: Docker Compose と環境設定（.env）の軽量化・整合性回復
- **Part 3 (Step 15-22)**: マルチメディア機能のプラグイン疎結合化
- **Part 4 (Step 23-28)**: CLI・監視・ヘルスチェックの整理
- **Part 5 (Step 29-34)**: ドキュメントの刷新と真実性の回復
- **Part 6 (Step 35-36)**: E2E（企画〜納品ZIP）総合出荷検証

---

## Part 1: ローカル起動スクリプトの完全修復と安定化 (Step 1-8)

### Step 1: `アプリ起動_ローカル.bat` の失敗原因特定
- **目的**: `--skip-migrations` オプション不整合および Huey ワーカー起動失敗のメカニズムを解明。
- **対象ファイル**: `アプリ起動_ローカル.bat`, `src/backend/tasks/huey.py`
- **変更内容**: バッチファイル内で `python -m huey.bin.huey_consumer` を呼ぶ際の環境変数設定と引数の不整合を記録。
- **検証コマンド**: コマンドプロンプトでの引数パース確認。

### Step 2: 共通環境検証スクリプト `scripts/check_env.py` の作成
- **目的**: Pythonバージョン（>=3.12）、仮想環境の有無、ポート空き状況（8200, 5173）を事前に検査する自己診断スクリプトを作成。
- **対象ファイル**: `scripts/check_env.py` (新規作成)
- **変更内容**: 検査結果を JSON またはカラー表示で返却し、前提条件不足時は明確な解決策を提示。
- **検証テスト**: `tests/unit/scripts/test_check_env.py` (新規作成)
- **実行コマンド**: `python scripts/check_env.py`

### Step 3: SQLite 自動マイグレーションスクリプト `scripts/init_db.py` の作成
- **目的**: 初回起動時に Alembic マイグレーションを安全かつ確実に実行するスクリプト。
- **対象ファイル**: `scripts/init_db.py` (新規作成)
- **変更内容**: テーブルが存在しない場合のみ `alembic upgrade head` を実行し、既存DBへの破壊的干渉を防止。
- **検証テスト**: `tests/unit/scripts/test_init_db.py` (新規作成)
- **実行コマンド**: `python scripts/init_db.py`

### Step 4: PowerShell ベースの堅牢な起動スクリプト `scripts/start_local.ps1` の作成
- **目的**: バックエンド、Huey ワーカー、フロントエンド開発サーバーを協調起動するメインランナーを作成。
- **対象ファイル**: `scripts/start_local.ps1` (新規作成)
- **変更内容**:
  1. 仮想環境 `.venv` の自動検出とアクティベーション。
  2. 環境変数（`HUEY_BACKEND=sqlite`, `DATABASE_URL=sqlite:///...`）の確実なセット。
  3. 各プロセスのジョブオブジェクト管理（親プロセス終了時の孤立防止）。
- **検証コマンド**: `powershell -ExecutionPolicy Bypass -File scripts/start_local.ps1 -DryRun`

### Step 5: `アプリ起動_ローカル.bat` のラッパー化
- **目的**: ダブルクリック起動時に `scripts/start_local.ps1` を安全に呼び出す薄いシムへ置換。
- **対象ファイル**: `アプリ起動_ローカル.bat`
- **変更内容**:
  ```bat
  @echo off
  cd /d "%~dp0"
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_local.ps1
  pause
  ```
- **検証コマンド**: バッチファイル構文の確認。

### Step 6: 安全な停止スクリプト `scripts/stop_local.ps1` および `アプリ停止.bat` の作成
- **目的**: ポート 8200, 5173 を占有している Uvicorn, Vite, Huey プロセスを安全に終了するスクリプト。
- **対象ファイル**: `scripts/stop_local.ps1`, `アプリ停止.bat` (新規作成)
- **変更内容**: PID を探索して Graceful Termination（SIGTERM相当）を送信。
- **検証コマンド**: プロセス停止のテスト実行。

### Step 7: ローカル起動プロセスの自動検証テスト作成
- **目的**: 起動スクリプトが正常に 3 つのプロセスを立ち上げ、ヘルスチェックが通ることを検証する統合テスト。
- **対象ファイル**: `tests/integration/test_local_startup.py` (新規作成)
- **テスト内容**: `start_local.ps1` をサブプロセスで起動し、`http://localhost:8200/health` が 200 OK を返すこと、終了スクリプトで正常停止することを検証。
- **実行コマンド**: `pytest tests/integration/test_local_startup.py`

### Step 8: README の「非推奨」警告の削除とクイックスタート手順の改訂
- **目的**: [README.md (L52-L60)](file:///e:/hhh/README.md#L52-L60) にある「Windows ワンクリック起動（非推奨：既知の問題あり）」を削除し、正式な起動手順として認定。
- **対象ファイル**: `README.md`
- **変更内容**: ワンクリック起動の手順を最新バッチに対応させて再記載。
- **検証コマンド**: README のプレビュー確認。

---

## Part 2: Docker Compose と環境設定の軽量化・整合性回復 (Step 9-14)

### Step 9: `.env.example` のバージョンと設定項目の同期
- **目的**: `.env.example` に残っていた旧バージョン（`4.9.0`）を現行バージョン（`5.0.3`）へ更新し、不要設定を削除。
- **対象ファイル**: `.env.example`
- **変更内容**: Apache AGE 関連などの不要変数を削除し、必須・オプショナルの区分けを明確化。
- **検証コマンド**: `python -c "from src.backend.config import settings"`

### Step 10: `docker-compose.yml` の開発用軽量化
- **目的**: メモリ制限を設定し、開発マシンのリソース圧迫を防止。
- **対象ファイル**: `docker-compose.yml`
- **変更内容**:
  ```yaml
  services:
    backend:
      deploy:
        resources:
          limits:
            memory: 1024M
    chromadb:
      deploy:
        resources:
          limits:
            memory: 512M
  ```
- **検証コマンド**: `docker compose config`

### Step 11: `Dockerfile` のマルチステージビルド最適化
- **目的**: ビルドキャッシュの効率化と最終イメージサイズの半減。
- **対象ファイル**: `Dockerfile`
- **変更内容**: `builder` ステージでホイールをビルドし、`runner` ステージでは最小限のランタイムのみをコピー。
- **検証コマンド**: `docker build -t autonovel:test -f Dockerfile . --dry-run` または構文検査。

### Step 12: コンテナ間ヘルスチェック依存関係の厳格化
- **目的**: PostgreSQL や Redis の準備完了前にバックエンドが起動してクラッシュするのを防ぐ `condition: service_healthy` の設定。
- **対象ファイル**: `docker-compose.yml`, `docker-compose.prod.yml`
- **変更内容**: `depends_on` に `condition: service_healthy` を適用。
- **検証コマンド**: Compose ファイルの妥当性確認。

### Step 13: Docker 起動・停止バッチ（`start_docker.bat`, `stop_docker.bat`）の改修
- **目的**: 環境変数未設定時の警告と、ビルドキャッシュ活用オプションの追加。
- **対象ファイル**: `start_docker.bat`, `stop_docker.bat`
- **変更内容**: `.env` ファイル不在時に `.env.example` からのコピーを促すガードを追加。
- **検証コマンド**: バッチ構文の確認。

### Step 14: Docker 構成検証テストの作成
- **目的**: Compose 設定が常に妥当な構文を保っていることを検証。
- **対象ファイル**: `tests/unit/infrastructure/test_docker_compose_valid.py` (新規作成)
- **テスト内容**: `docker compose config` コマンドが終了コード 0 を返すことをテスト。
- **実行コマンド**: `pytest tests/unit/infrastructure/test_docker_compose_valid.py`

---

## Part 3: マルチメディア機能のプラグイン疎結合化 (Step 15-22)

### Step 15: プラグインインターフェース `PluginProtocol` の定義
- **目的**: コア機能とオプショナル拡張（マルチメディア、外部投稿等）の境界を確立。
- **対象ファイル**: `src/interfaces/plugin.py` (新規作成)
- **変更内容**: `initialize()`, `is_available()`, `shutdown()` メソッドを持つプロトコルを定義。
- **検証テスト**: `tests/unit/interfaces/test_plugin_protocol.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/interfaces/test_plugin_protocol.py`

### Step 16: 画像プロバイダ共通抽象 `ImageProviderProtocol` の定義
- **目的**: Imagen, DALL-E, SD WebUI, ComfyUI を統一的に扱うインターフェースを作成。
- **対象ファイル**: `src/interfaces/image_provider.py` (新規作成)
- **変更内容**: `async def generate_image(prompt: str, ...) -> str` を定義。
- **検証テスト**: `tests/unit/interfaces/test_image_provider_protocol.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/interfaces/test_image_provider_protocol.py`

### Step 17: `MultimediaService` のプラグインカプセル化
- **目的**: コアバックエンドから `MultimediaService` をオプショナルプラグインとして切り離し。
- **対象ファイル**: `src/plugins/multimedia/service.py`
- **変更内容**: `require_multimedia()` で毎回エラーを投げるのではなく、プラグインレジストリで有効時のみルーターにマウント。
- **検証テスト**: `tests/unit/plugins/test_multimedia_plugin.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/plugins/test_multimedia_plugin.py`

### Step 18: プラグインレジストリ `PluginRegistry` の構築
- **目的**: 設定（環境変数・機能フラグ）に基づいてプラグインを動的にロード・無効化する仕組み。
- **対象ファイル**: `src/core/plugin_registry.py` (新規作成)
- **変更内容**: プラグインの自動探索とロード状態管理。
- **検証テスト**: `tests/unit/core/test_plugin_registry.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/core/test_plugin_registry.py`

### Step 19: マルチメディア無効時の FastAPI ルーター軽量化
- **目的**: マルチメディアが無効な場合、不要なDB初期化やタスク登録をスキップ。
- **対象ファイル**: `src/backend/server.py`
- **変更内容**: `if plugin_registry.is_enabled("multimedia"): app.include_router(multimedia.router)` のように条件付きマウント。
- **検証テスト**: `tests/unit/api/test_plugin_conditional_routing.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/api/test_plugin_conditional_routing.py`

### Step 20: 音声合成プロバイダ（VOICEVOX等）のプラグイン化
- **目的**: `test_voicevox_pipeline.py` で落ちていた音声合成機能をオプショナルプラグインへ整理。
- **対象ファイル**: `src/plugins/audio/voicevox.py`
- **変更内容**: VOICEVOX サーバー不在時の Graceful Fallback（空ファイル生成またはスキップ）を実装。
- **検証テスト**: `tests/unit/test_voicevox_pipeline.py`
- **実行コマンド**: `pytest tests/unit/test_voicevox_pipeline.py`

### Step 21: プラグイン完全無効化時のコアドメイン単体テスト
- **目的**: すべての外部オプショナルプラグインをオフにした状態で、小説の生成・保存・エクスポートが最速で完結することを保証。
- **対象ファイル**: `tests/unit/core/test_core_without_plugins.py` (新規作成)
- **テスト内容**: プラグイン 0 件の状態で `create_easy_mode_pipeline` を実行し、完全成功することを確認。
- **実行コマンド**: `pytest tests/unit/core/test_core_without_plugins.py`

### Step 22: プラグイン隔離検証のオールグリーン確認
- **目的**: プラグイン関連の全テストがパスすることを確認。
- **対象テスト**: `tests/unit/plugins/`, `tests/unit/interfaces/`
- **実行コマンド**: `pytest tests/unit/plugins/ tests/unit/interfaces/`

---

## Part 4: CLI・監視・ヘルスチェックの整理 (Step 23-28)

### Step 23: CLI エントリポイントの統一 (`src/cli/main.py`)
- **目的**: バラバラに定義されていたCLIスクリプト（`dsp-balance`, `csp-balance`, `grammar-balance` 等）を単一コマンド `autonovel` のサブコマンドとして統合。
- **対象ファイル**: `src/cli/main.py` (新規作成)
- **変更内容**: `argparse` または `click` によるサブコマンド構成（`autonovel balance ...`, `autonovel export ...`）。
- **検証テスト**: `tests/unit/cli/test_cli_main.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/cli/test_cli_main.py`

### Step 24: `pyproject.toml` の `[project.scripts]` の更新
- **目的**: 統一CLI `autonovel = "src.cli.main:main"` を登録。
- **対象ファイル**: `pyproject.toml`
- **変更内容**: 旧スクリプトのエイリアスを維持しつつ、主エントリポイントを追加。
- **検証コマンド**: `pip install -e .` 後に `autonovel --help` 実行確認。

### Step 25: `/health` エンドポイントの最適化と軽量化
- **目的**: 外部依存（Huey, Redis, DB）の1つが遅延してもヘルスチェックがタイムアウトしないように、非同期並行チェック（`asyncio.gather` + `timeout`）を適用。
- **対象ファイル**: `src/backend/observability/health.py`
- **変更内容**: 各コンポーネントのタイムアウトを 1.0 秒に制限。
- **検証テスト**: `tests/unit/api/test_health_timeout.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/api/test_health_timeout.py`

### Step 26: プロセス内メトリクス（`/metrics`）のメモリリーク防止
- **目的**: 長時間稼働時にメトリクスカウンタが肥大化しないよう、固定キー集計に限定。
- **対象ファイル**: `src/backend/observability/health.py`
- **変更内容**: 動的ラベル生成の抑制とリングバッファ化。
- **検証テスト**: `tests/unit/api/test_metrics_memory.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/api/test_metrics_memory.py`

### Step 27: CLI コマンドの網羅的単体テスト
- **目的**: 全サブコマンドがヘルプ表示および異常系ハンドリングを正しく行うことを検証。
- **対象ファイル**: `tests/unit/cli/test_cli_all_subcommands.py` (新規作成)
- **テスト内容**: `autonovel --version`, `autonovel balance --help`, `autonovel export --help` を実行。
- **実行コマンド**: `pytest tests/unit/cli/`

### Step 28: 観測可能性テストの実行確認
- **目的**: ヘルスチェックとメトリクス関連テストの完全パス確認。
- **対象テスト**: `tests/unit/api/test_health*.py`, `tests/unit/api/test_metrics*.py`
- **実行コマンド**: `pytest tests/unit/api/ -k "health or metrics"`

---

## Part 5: ドキュメントの刷新と真実性の回復 (Step 29-34)

### Step 29: `README.md` の全面改訂（クリーンアップ）
- **目的**: 過去のレガシー技術（Apache AGE 等）の言及を削除し、最新のアーキテクチャ図と簡潔なセットアップ手順に刷新。
- **対象ファイル**: `README.md`
- **変更内容**:
  1. 新規バッチによる 1 クリック起動ガイド。
  2. コア機能（執筆・4層圧縮・整形・エクスポート）を前面に押し出した明快な説明。
- **検証コマンド**: Markdown リンターまたはプレビュー確認。

### Step 30: 開発者ガイド `docs/development_guide.md` の新規作成
- **目的**: 新規参画者が 15 分で環境構築してテストを実行できるオンボーディング資料。
- **対象ファイル**: `docs/development_guide.md` (新規作成)
- **変更内容**: Python 3.12 仮想環境作成、依存インストール、テスト実行、コーディング規約（Ruff, Mypy）を記載。
- **検証コマンド**: ドキュメントのリンク整合性チェック。

### Step 31: 最新の OpenAPI 仕様書の再エクスポート
- **目的**: バックエンドルーター整理後の正確な API スキーマを生成。
- **対象ファイル**: `docs/openapi.json`
- **実行コマンド**: `python scripts/export_openapi.py`

### Step 32: フロントエンド型定義の自動再生成
- **目的**: 最新の `docs/openapi.json` から TypeScript の API 型定義を同期更新。
- **対象ファイル**: `frontend/src/types/api.generated.ts`
- **実行コマンド**: `cd frontend && npm run generate:api-types`

### Step 33: `CHANGELOG.md` の v5.1.0 リリースノート追記
- **目的**: P1〜P3 で実施した負債解消・アーキテクチャ統合・運用スリム化の全成果を記録。
- **対象ファイル**: `CHANGELOG.md`
- **変更内容**: v5.1.0 "Stabilization and Architectural Consolidation" の項目を追加。
- **検証コマンド**: CHANGELOG のフォーマット確認。

### Step 34: リンターおよび静的型チェックのオールグリーン確認
- **目的**: バックエンド・フロントエンドの全静的解析を通過。
- **実行コマンド**:
  - `ruff check .`
  - `ruff format --check .`
  - `mypy src`
  - `cd frontend && npm run lint && npm run typecheck`

---

## Part 6: E2E（企画〜納品ZIP）総合出荷検証 (Step 35-36)

### Step 35: E2E 小説生成・納品パイプライン自動テストの作成
- **目的**: ユーザーが Web UI または API で行う一連のワークフロー（企画設定入力 → プロット生成 → 4層圧縮コンテキスト構築 → 本文執筆 → なろう/カクヨム整形 → ZIP納品ダウンロード）をエンドツーエンドで自動検証。
- **対象ファイル**: `tests/e2e/test_full_novel_production_pipeline.py` (新規作成)
- **テスト内容**: モックLLM環境でパイプラインを走らせ、生成された ZIP ファイルを展開して各章の本文・メタデータ・設定集が正しく揃っていることをアサート。
- **実行コマンド**: `pytest tests/e2e/test_full_novel_production_pipeline.py`

### Step 36: 全体回帰テストスイートの最終出荷検証（Grand Verification）
- **目的**: P1, P2, P3 の全改修を経たコードベースにおいて、単体・統合・E2Eの全テストが 100% 成功することを最終確認。
- **対象ディレクトリ**: `tests/` 全体
- **実行コマンド**: `pytest -v --tb=short`
- **合格基準**:
  - `failed=0, errors=0`
  - テスト実行時間 < 180秒
  - 全 108 ステップの完全達成を確認し、プロジェクトの安定化完了とする。
