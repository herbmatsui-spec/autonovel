# 開発者ガイド - 覇権小説エンジン v3.3

## 目次
1. [プロジェクト概要](#プロジェクト概要)
2. [開発環境セットアップ](#開発環境セットアップ)
3. [プロジェクト構成](#プロジェクト構成)
4. [開発ワークフロー](#開発ワークフロー)
5. [コード規約](#コード規約)
6. [テスト実行](#テスト実行)
7. [デバッグ・トラブルシューティング](#デバッグトラブルシューティング)
8. [アーキテクチャ概要](#アーキテクチャ概要)
9. [よくある質問 (FAQ)](#よくある質問-faq)

---

## プロジェクト概要

覇権小説エンジンは、AI を活用した小説自動生成システムです。

- **かんたんモード**: ジャンル選択のみで企画から完結まで全自動生成
- **上級者モード**: 詳細カスタマイズ・手動承認・分岐・メディアミックス対応
- **技術スタック**: Python 3.12, FastAPI, SQLAlchemy, Huey, ChromaDB, Redis
- **LLM**: Gemini 2.5 Pro/Flash, OpenRouter (Claude, GPT 等)

---

## 開発環境セットアップ

### 前提条件

- Python 3.12+
- Redis (ローカル開発用)
- SQLite (本番は PostgreSQL)
- Google Gemini API キー (または OpenRouter キー)

### セットアップ手順

```bash
# リポジトリクローン
git clone <repo-url>
cd autonovel

# 仮想環境作成
python -m venv .venv
source .venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 開発用依存関係 (テスト・lint 等)
pip install -r requirements-dev.txt  # 存在する場合

# 環境変数設定
cp .env.example .env
# .env を編集して API キー等を設定

# データベース初期化
python -c "from src.backend.database import init_db; from src.core.container import AppContainer; init_db(AppContainer.db().db_path)"

# ストレージディレクトリ作成
mkdir -p storage/db chroma_db

# サーバー起動
uvicorn src.backend.server:app --reload --host 0.0.0.0 --port 8200
```

### 環境変数 (`.env`)

```bash
# 必須
KAKU_GEMINI_API_KEY=your_gemini_api_key
# または
KAKU_OPENAI_API_KEY=your_openrouter_key
KAKU_OPENAI_BASE_URL=https://openrouter.ai/api/v1

# オプション (デフォルト値あり)
KAKU_DATABASE_URL=sqlite+aiosqlite:///./autonovel.db
KAKU_REDIS_URL=redis://localhost:6379/0
KAKU_LOG_LEVEL=INFO
KAKU_API_HOST=0.0.0.0
KAKU_API_PORT=8200
KAKU_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8501
```

---

## プロジェクト構成

```
autonovel/
├── src/
│   ├── backend/                 # バックエンド (FastAPI)
│   │   ├── server.py           # エントリーポイント・ミドルウェア・ルーター
│   │   ├── engine.py           # UltimateHegemonyEngine (DI ファサード)
│   │   ├── engine_facade.py    # Engine ファサード
│   │   ├── engine_*.py         # エンジンコンポーネント (narrative, critique, style_rag 等)
│   │   ├── auth.py             # 認証・レート制限
│   │   ├── background.py       # バックグラウンドレポーター
│   │   ├── database/           # DB層 (Repository, Manager)
│   │   ├── error_handlers.py   # 例外ハンドラー
│   │   ├── observability/      # メトリクス・ミドルウェア
│   │   ├── routers/            # API ルーター (easy_mode, plots, episodes, marketing)
│   │   ├── worker_config.py    # Huey 設定
│   │   └── llm_client.py       # LLM クライアントアダプター
│   ├── core/
│   │   ├── container/          # DI コンテナ (app.py, infra.py)
│   │   ├── llm_gateway.py      # LLM 生成統一プロキシ
│   │   ├── llm_clients/        # LLM クライアント (Gemini, OpenAI)
│   │   ├── async_utils.py      # 並行制御ユーティリティ
│   │   ├── exceptions.py       # 例外階層
│   │   ├── opentelemetry.py    # OpenTelemetry 設定
│   │   └── observability.py    # 構造化ログ・トレース
│   ├── easy_mode/              # かんたんモード
│   │   ├── pipeline.py         # オーケストレーター
│   │   ├── bible_generator.py
│   │   ├── plot_generator.py
│   │   ├── episode_writer.py
│   │   ├── episode_auditor.py
│   │   ├── episode_rewriter.py
│   │   ├── series_finalizer.py
│   │   ├── progress_reporter.py
│   │   ├── spice_guard/        # 尖り保護システム
│   │   └── models.py           # 共通データクラス
│   ├── agents/                 # エージェント (Planning, Writing, Marketing 等)
│   ├── prompts/                # プロンプト管理
│   ├── services/               # サービス層 (Bible, Plot, etc.)
│   ├── models/                 # 共通モデル (base.py 等)
│   └── llm/                    # LLM 関連 (model_router 等)
├── config/
│   ├── settings.py             # 統一設定クラス (pydantic-settings)
│   ├── constants.py            # 定数定義 (後方互換エイリアス含む)
│   ├── project_context.py      # 設定アクセサ (後方互換)
│   ├── validator.py            # 設定バリデータ
│   ├── cors_config.py          # CORS 設定
│   ├── logging_config.py       # ログ設定
│   ├── settings.toml           # 設定ファイル (SSOT)
│   └── presets/                # ジャンル別プリセット (9ジャンル)
├── schemas/
│   └── config.py               # Pydantic 設定モデル (GlobalConfigModel)
├── tests/                      # テストコード
│   ├── unit/                   # 単体テスト
│   ├── integration/            # 統合テスト (Testcontainers 対応予定)
│   └── e2e/                    # E2E テスト (Playwright 予定)
├── docs/
│   └── architecture/           # C4 アーキテクチャ図・シーケンス図
├── requirements.txt
├── requirements-dev.txt        # 開発用依存関係
├── pyproject.toml              # ビルド設定・ツール設定
└── README.md
```

---

## 開発ワークフロー

### ブランチ戦略

```
main (本番)
  ↑
  ├── develop (開発統合)
  │     ↑
  │     ├── feature/xxx (機能開発)
  │     ├── fix/xxx (バグ修正)
  │     └── refactor/xxx (リファクタリング)
  │
  └── release/vX.Y.Z (リリース準備)
```

### コミットメッセージ規約

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`

**例**:
```
feat(pipeline): add SpiceGuard integration to episode rewrite

- Extract spice elements before rewrite
- Inject protection markers
- Remove markers after rewrite

Closes #123
```

### PR チェックリスト

- [ ] テストが追加・更新されている
- [ ] `mypy --strict` でエラーなし
- [ ] `ruff check` でエラーなし
- [ ] ドキュメント更新 (必要な場合)
- [ ] CHANGELOG.md 更新 (機能追加・破壊的変更時)

---

## コード規約

### Python コードスタイル

- **Formatter**: `ruff format` (Black 互換)
- **Linter**: `ruff check` (Flake8 + isort + 独自ルール)
- **Type Checker**: `mypy --strict`
- **Line Length**: 100 文字
- **Import Order**: `ruff` デフォルト (標準ライブラリ → サードパーティ → ローカル)

### 型ヒント

- **全関数に型ヒント必須** (引数・戻り値)
- `mypy --strict` でエラー 0 を維持
- `Any` 禁止 (`Union`, `Optional`, `Any` の代替を使用)
- `@overload` 活用 (複数シグネチャがある場合)

```python
# Good
async def generate_json(
    self,
    purpose_or_request: Union[str, LLMRequestOptions] = "writing",
    prompt: str = "",
    response_schema: Any = None,
) -> GenerateResult: ...

# Bad
async def generate_json(self, purpose="writing", **kwargs): ...
```

### 非同期コード

- `async def` で定義
- `asyncio.sleep` 使用 (blocking `time.sleep` 禁止)
- `asyncio.Semaphore` で並行制御 (`limit_concurrency` ユーティリティ使用)
- ループ内での `await` は最小限に (バッチ処理推奨)

```python
# Good
async def process_all(items: List[Item]) -> List[Result]:
    semaphore = asyncio.Semaphore(5)
    async def limited(item):
        async with semaphore:
            return await process_one(item)
    return await asyncio.gather(*[limited(i) for i in items])
```

### エラーハンドリング

- 基底例外: `HegemonyError` (status_code, error_code, original)
- 専用例外クラス使用 (`BibleGenerationError`, `EpisodeWritingError` 等)
- `except Exception` 禁止 (具体的な例外を捕捉)
- ログ: `logger.warning/error(..., extra={"error_code": ..., "trace_id": ...})`

```python
# Good
try:
    result = await llm.generate_json(...)
except LLMTimeoutError as e:
    logger.warning("LLM timeout", extra={"error_code": "LLM_TIMEOUT", "original": str(e)})
    raise BibleGenerationError("Bible generation timeout", original=e) from e
except LLMError as e:
    logger.error("LLM error", extra={"error_code": e.error_code, "original": str(e)})
    raise

# Bad
try:
    result = await llm.generate_json(...)
except Exception as e:
    logger.warning(f"Failed: {e}")  # 詳細なし
    return fallback()
```

### 依存性注入 (DI)

- `dependency-injector` 使用
- コンテナ: `InfraContainer` (インフラ), `AppContainer2` (アプリ)
- 全依存をコンストラクタで明示的に受け取り
- `providers.Factory` で遅延生成 (非同期プリミティブ等)
- `providers.Callable` で設定値から導出値生成

### 設定管理

- 単一真実源: `config.settings.Settings` (pydantic-settings.BaseSettings)
- 環境変数プレフィックス: `KAKU_`
- 旧 `constants.py` は後方互換エイリアスのみ (段階的移行中)
- `GlobalConfigModel` は `schemas.config` に移動済み (後方互換ラッパーあり)

---

## テスト実行

### テスト構成

```
tests/
├── unit/                    # 単体テスト (モック使用, 高速)
│   ├── test_engine_init.py
│   ├── test_llm_gateway.py
│   └── ...
├── integration/             # 統合テスト (実DB/Redis/ChromaDB)
│   └── ...
├── e2e/                     # E2E テスト (Playwright, 全フロー)
│   └── ...
├── test_phase1_preset_integration.py
├── test_phase2_pipeline_integration.py
├── test_phase3_asset_pack.py
├── test_auth.py
├── test_constants.py
├── test_config_loading.py
└── test_minimal.py
```

### 実行コマンド

```bash
# 全テスト
pytest

# 特定テスト
pytest tests/unit/test_engine_init.py -v

# マーカー指定
pytest -m "not slow"           # 低速テスト除外
pytest -m "integration"        # 統合テストのみ

# カバレッジ
pytest --cov=src --cov-report=html --cov-fail-under=80

# 並列実行 (xdist)
pytest -n auto

# 特定テストのデバッグ
pytest tests/unit/test_engine_init.py::TestEngineConstructor::test_new_constructor_with_all_dependencies -v -s
```

### テスト作成指針

- **単体テスト**: 外部依存をモック、高速 (< 100ms/test)
- **統合テスト**: Testcontainers で実 DB/Redis/ChromaDB 使用
- **E2E テスト**: Playwright でフロントエンド含む全フロー
- **モック最小化**: 実装詳細に依存しないテスト
- **決定論的**: 乱数・時刻は固定・モック化

---

## デバッグ・トラブルシューティング

### よくある問題と解決

| 症状 | 原因 | 解決 |
|------|------|------|
| `ModuleNotFoundError` | 依存未インストール / PYTHONPATH | `pip install -r requirements.txt`, `PYTHONPATH=.` |
| `ImportError: cannot import ConfigManager` | 旧インポートパス | `from config.settings import ConfigManager` |
| `LLMTimeoutError` | API 遅延・制限 | リトライ設定確認, API キー確認 |
| `BibleGenerationError` | LLM 応答不正 | プロンプト確認, フォールバック動作確認 |
| `RuntimeError: Cancelled` | キャンセル処理 | `_cancelled` フラグ確認, `cancel()` 呼び出し |
| `asyncio.Semaphore` エラー | イベントループ前生成 | `providers.Factory` で遅延生成 |

### ログ・トレース確認

```bash
# 構造化ログ (JSON)
tail -f logs/app.log | jq .

# トレース ID でフィルタ
grep "trace_id.*abc123" logs/app.log

# メトリクス確認
curl http://localhost:8200/metrics | grep kaku_
```

### OpenTelemetry トレース

```bash
# コンソールエクスポーター有効化 (開発用)
KAKU_OTEL_CONSOLE_EXPORTER=true python -m src.backend.server
```

### データベース直接確認

```bash
# SQLite
sqlite3 autonovel.db ".tables"
sqlite3 autonovel.db "SELECT * FROM books LIMIT 5;"

# ChromaDB
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma_db')
for col in client.list_collections():
    print(col.name, col.count())
"
```

---

## アーキテクチャ概要

### レイヤー構造

```
┌─────────────────────────────────────┐
│ API 層 (FastAPI Router + Middleware) │
├─────────────────────────────────────┤
│ パイプライン層 (Orchestration)        │
│  EasyModePipeline / AdvancedPipeline │
├─────────────────────────────────────┤
│ 生成層 (Generators)                   │
│  BibleGen / PlotGen / Writer / Auditor / Rewriter / Finalizer │
├─────────────────────────────────────┤
│ エンジンコア (Engine Core)             │
│  LLMGateway / SpiceGuard / Factory / Cache │
├─────────────────────────────────────┤
│ LLM / データ / 外部サービス             │
│  LLM Clients / Repository / VectorStore / External APIs │
└─────────────────────────────────────┘
```

### 依存性の方向性

```
API Router → Pipeline → Generators → Engine Core → LLM Clients / Data / External
                    ↑
              DI Container (AppContainer2)
```

### 主要インターフェース

| インターフェース | 実装 | 用途 |
|----------------|------|------|
| `BaseLLMClient` | `GeminiApiClient`, `OpenAIApiClient` | LLM 生成統一 |
| `DataRepository` | `DataRepository` (impl) | CRUD 抽象化 |
| `VectorStore` | `ChromaVectorStore` | ベクトル検索 |
| `LLMGenerateResultProxy` | `LLMGenerateResultProxy` | 生成統一プロキシ |

---

## よくある質問 (FAQ)

### Q: 新しいジャンルを追加するには？
**A**: `config/presets/<genre>/` 配下に必要なプリセットファイルを作成:
- `bible/bible_preset_<genre>.j2`
- `tension/tension_curve_<genre>.yaml`
- `style/style_dna_preset_<genre>.j2`
- `hooks/hook_params_<genre>.json`
- `erotic/erotic_rules_<genre>_kakuyomu.yaml`
- `characters/char_archetypes_<genre>.json`
- `titles/title_vars_<genre>.json`
- `marketing/marketing_vars_<genre>.json`
- `episode_structure/episode_structure_<genre>.yaml`

### Q: 新しい LLM プロバイダーを追加するには？
**A**:
1. `src/core/llm_clients/` に `BaseLLMClient` 継承クラス作成
2. `src/core/llm_gateway.py` の `LLMProviderFactory.get_client()` に追加
3. `is_openai_compatible()` で判定ロジック調整

### Q: カスタムプロンプトテンプレートを使うには？
**A**: `config/presets/<genre>/bible/bible_preset_<genre>.j2` 等の Jinja2 テンプレートを編集。変数は `_get_preset_defaults()` で注入。

### Q: 監査スコアの閾値を変えるには？
**A**: `PipelineConfig(target_audit_score=90.0)` で指定、または環境変数 `KAKU_TARGET_AUDIT_SCORE=90`。

### Q: 並行実行数を増やすには？
**A**: 環境変数 `KAKU_MAX_CONCURRENT_API_CALLS=10` (デフォルト 5)。セマフォは `Factory` で遅延生成。

### Q: デバッグ用に LLM プロンプトを見たい
**A**: `KAKU_LOG_LEVEL=DEBUG` で構造化ログ出力。`extra={"prompt": prompt, "variables": variables}` に含まれる。

### Q: 本番デプロイ時の注意点
**A**:
- `KAKU_LOG_LEVEL=WARNING` 以上推奨
- `KAKU_OTEL_CONSOLE_EXPORTER=false` (OTLP エクスポーター使用)
- `KAKU_DATABASE_URL` に PostgreSQL 指定
- `KAKU_REDIS_URL` に Redis クラスタ指定
- `KAKU_CORS_ALLOWED_ORIGINS` で本番オリジンのみ許可
- `KAKU_FAIL_FAST_MODE=true` で早期失敗

---

## リンク集

- [アーキテクチャ図 (C4)](docs/architecture/)
- [シーケンス図](docs/architecture/sequences/)
- [データフロー図](docs/architecture/data-flow.md)
- [実装計画書](IMPLEMENTATION_PLAN_CODE_REVIEW_48_STEPS.md)
- [コードレビュー](CODE_REVIEW_DETAILED.md)
- [CI/CD パイプライン](.github/workflows/ci.yml)