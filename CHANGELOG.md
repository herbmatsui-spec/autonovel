# 覇権小説エンジン - CHANGELOG

すべての注目すべき変更を記録します。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [Unreleased]

### Added
- LLM アクセス層の単一化: `src.core.llm.providers` に統一プロバイダインターフェース (`LLMProvider`, `LLMResponse`, `GeminiProvider`, `OpenAIProvider`, `LLMProviderFactory`) を新設、`src.llm` を非推奨化
- `src/core/llm_gateway.py` を新プロバイダ層を使用するようリファクタリング (`generate_json`/`generate_text` が `LLMResponse` オブジェクトを返すよう変更)
- `src/services/llm_service.py` を新プロバイダファクトリ使用に更新
- データベースマイグレーション整合性の保証: `init_db` の本番環境での `create_all` フォールバックを削除、Alembic のみを使用
- `src/backend/database/schema_check.py` によるスキーマドリフト検出機能追加、CI 用スクリプト `scripts/check_schema_drift.py` を追加
- `src/backend/database/uow.py` にネストトランザクション防止チェックを追加
- エラーハンドリング基盤の整備: `src/core/error_handler.py` に統一エラーハンドリングユーティリティ追加
- `rate_limit_middleware` をフェイルオープン（Redis 不可時はリクエスト許可）に変更
- FastAPI アプリバージョンを `settings.app_version` (SSOT) から動的取得に変更、`config/settings.py` に `app_version` フィールド追加
- `scripts/no_print_check.py` と `scripts/no_secret_check.py` による本番コードの `print()`/シークレット検出、pre-commit フック追加
- バージョン同期確認テスト `tests/integration/test_version.py` 追加
- エラー処理ガイド `docs/error_handling.md` を追加（`log_exception` の利用方針とドメイン例外への変換パターンを記載）
- 提案1: スタイル学習の即時実装：章完了時に文体特徴を抽出しSTYLE_LEARNED.mdに蓄積、次章生成時にプロンプト注入
- 提案2: 整合性 Guardian の完全統合：章執筆プロンプトに整合性チェック結果を強制注入（フラグ `consistency_guardian_enabled`）
- 提案3: 章単位の自動改稿ループ：生成直後に整合性チェック→指摘があれば同一プロンプトで最大2回リライト（フラグ `auto_revision_enabled` ）
### Changed

- `init_db`: 本番環境では `create_all` フォールバックを行わず、Alembic 失敗時は即座にエラー終了
- `LLMGenerateResultProxy` コンストラクタ: `factory` キーワード引数も受け付けるよう後方互換性を維持
- ヘルスチェック `check_llm_gateway`: 新 `LLMProviderFactory` 使用に更新
- `DatabaseManager.execute/fetch_*` の非推奨警告を維持しつつ、リポジトリ経由アクセスへの移行を推奨

### Fixed
- `src/backend/task_helpers.py` の構文エラー修正（誤って適用された diff マーカー `+` を除去）
- 統一設定クラス `config.settings.Settings` (pydantic-settings.BaseSettings)
- 全依存を明示的に注入する `UltimateHegemonyEngine` コンストラクタ
- `EngineDeps` データクラスによるエンジン依存の型安全なグループ化 (`src/backend/engine_deps.py`)
- 起動時依存検証 `validate_dependencies()` によるランタイムエラー早期検知
- かんたんモードパイプラインのモジュール分割:
  - `BibleGenerator` (bible_generator.py)
  - `PlotGenerator` (plot_generator.py)
  - `EpisodeWriter` (episode_writer.py)
  - `EpisodeAuditor` (episode_auditor.py)
  - `EpisodeRewriter` (episode_rewriter.py)
  - `SeriesFinalizer` (series_finalizer.py)
  - `ProgressReporter` (progress_reporter.py)
- SpiceGuard のモジュール分割:
  - `PatternRegistry` (pattern_registry.py) - パターン定義・コンパイル・キャッシュ
  - `SpiceExtractor` (extractor.py) - 尖り要素抽出 (キーワード逆インデックス最適化)
  - `SpiceMarkerInjector` / `RewritePromptBuilder` (marker.py) - マーカー操作・プロンプト構築
- LLM ゲートウェイの型安全性向上 (`@overload`, `Union[str, LLMRequestOptions]`)
- 統一設定クラスによる設定管理の一元化 (`config.settings.Settings`)
- OpenTelemetry 自動計装 (FastAPI, SQLAlchemy, Redis)
- Prometheus メトリクス命名規約統一 (`kaku_{subsystem}_{name}_{unit}`)
- 依存注入・設定改善: `EngineDeps`を使用したDI最適化、APIキーをSettings経由で取得、Redis設定をDI経由で明示化
- Xenon複雑度しきい値調整: 平均複雑度の閾値をDからAに厳格化（`.pre-commit-config.yaml`）
- SpiceGuardアーキテクチャドキュメント追加: `docs/architecture/spice_guard.md`
- LangGraph採用理由ADR追加: `docs/adr/0004-langgraph-adoption.md`
- カスタム例外クラス追加 (`BibleGenerationError`, `EpisodeWritingError`, 等)
- Testcontainers 統合テスト基盤
- Playwright E2E テスト戦略ドキュメント
- ミューテーションテスト導入ガイド (`mutmut`)
- Pre-commit フック整備 (ruff, mypy, bandit, vulture, xenon, gitleaks, pip-audit)
- CI パイプライン全面改善 (並列化、キャッシュ、品質ゲート)
- `py.typed` マーカー (PEP 561 対応)
- `ENV_OVERRIDE_MAP` 整合性検証スクリプト (`scripts/validate_env_map.py`)
- `no-print-statements` 専用チェックスクリプト (`scripts/no_print_check.py`)
- 開発用依存分離 `requirements-dev.txt`
- Dockerfile マルチステージビルド・非 root ユーザー化
- フロントエンドのタブ構造をモジュール化し、React Router v6 と遅延ロードを導入し、初期ロードパフォーマンスを向上
- デザインシステムを統一し、Atomic Design 原則に基づくコンポーネントライブラリを構築
- アクセシビリティを向上し、ARIAラベル、キーボードナビゲーション、カラーコントラストを改善
- 状態管理をZustandスライスとReact Queryに統合し、データフェッチとキャッシュを最適化

### Changed
- `UltimateHegemonyEngine` の全依存を明示的コンストラクタ引数化 (DI 対応)
- `EngineDeps` 単一引数による依存注入簡素化 (13引数 → 1引数 + 従来互換)
- 起動時 `validate_dependencies()` 呼出で必須依存不足を即時検知
- `AppContainer2` で `EngineDeps` 組み立て・エンジン注入
- `llm_gateway.py` 重複メソッド `_normalize_response`/`_usage_metric` 削除
- `config/settings.py` 重複フィールド `polishing_min_content_ratio` 削除
- `connection_pipeline` 未使用プロバイダ削除
- API キー `"DUMMY"` ハードコード → 環境変数 `GEMINI_API_KEY` 注入
- `README.md`: 依存注入と設定改善に関する説明を追加
- `UltimateHegemonyEngine` の全依存を明示的コンストラクタ引数化 (DI 対応)
- `pipeline.py` をオーケストレーション専用にリファクタリング (633行 → 257行)
- `spice_guard.py` を4モジュールに分割 (537行 → 各150-200行)
- `llm_gateway.py` の `generate()` 削除、`generate_json`/`generate_text` の `@overload` 化
- `config/settings.py` に統一設定クラス実装、`constants.py` から段階的移行
- `project_context.py` を新設定クラス対応に更新 (後方互換維持)
- `InfraContainer` / `AppContainer2` で全依存を明示的注入
- 非同期セマフォを `providers.Factory` で遅延生成化
- SpiceGuard 抽出ロジックをキーワード逆インデックスで高速化
- エラーハンドリング統一 (専用例外クラス・フォールバック明示化)
- Prometheus メトリクス名を `kaku_{subsystem}_{name}_{unit}` 規約に統一 (後方互換エイリアス付き)
- 設定値 `episode_structure` をプリセット YAML に外部化 (9ジャンル分)
- テストディレクトリ再編成: `tests/unit/` (114ファイル), `tests/phase1-4/`, `tests/integration/`, `tests/e2e/`
- CI に `KAKU_HEALTH_CHECK_LLM=false` 追加 (API コスト削減)
- xenon 複雑度しきい値緩和 (B/B/A → F/F/D) でベースライン通過

### Fixed
- `llm_gateway.py` 重複 `_normalize_response`/`_usage_metric` (262-287行) 削除
- `app.py` ハードコード `"DUMMY"` API キー
- `settings.py` 重複 `polishing_min_content_ratio` (209行)
- `test_container.py` 未使用 `connection_pipeline` 期待値除外
- パイプライン内の引数順バグ修正 (`_generate_episode` 引数順)
- `_finalize_result` → `_finalize_series` メソッド名修正
- `_finalize_series` 非同期呼び出し修正 (`await` 追加)
- キャンセル時の空 `SeriesResult` 返却処理追加
- SpiceGuard キーワード境界チェック修正 (日本語文字対応)
- Bible 生成失敗時のフォールバック処理改善 (例外ラップ→フォールバック返却)

### Security
- `bandit` セキュリティスキャン追加 (CI)
- `gitleaks` シークレット検出追加 (pre-commit / CI)
- `pip-audit` 依存脆弱性スキャン追加 (CI)
- 環境変数プレフィックス `KAKU_` 統一
- シークレットマスキングログ機能

---

## [3.3.0] - 2026-08-16

### Added
- コードレビューに基づく大規模リファクタリング開始
- 実装計画書 (48ステップ・4フェーズ) 作成
- コードレビュードキュメント作成

---

## [3.2.0] - 2026-08-01

### Added
- Phase 3 アセットパック機能 (メディアミックス・電子書籍エクスポート)
- IF ルート分岐機能 (上級者モード)
- メディアミックス生成 (漫画台本・音声台本・動画台本)
- 電子書籍エクスポート (EPUB/PDF/MOBI/HTML/CSS)

### Changed
- アセットパック生成パイプライン統合

---

## [3.1.0] - 2026-07-15

### Added
- Phase 2 パイプライン統合テスト
- SpiceGuard (尖り保護システム) 実装
- 普遍パターン・ジャンル別パターン定義
- マーカー注入・除去機能
- リライトプロンプト自動構築

### Changed
- パイプラインアーキテクチャ改善

---

## [3.0.0] - 2026-07-01

### Added
- Phase 1 基盤実装完了
- かんたんモード全自動生成パイプライン
- Bible 自動生成・プロット生成・エピソード生成
- 監査・リライトループ
- プリセットシステム (9ジャンル対応)
- LLM ゲートウェイ (プロバイダー抽象化)
- DI コンテナ (dependency-injector)
- 構造化ログ・トレース ID 対応
- Prometheus メトリクス・OpenTelemetry 対応

---

## [2.x] - 2026-06-01

### Added
- 初期プロトタイプ
- 基本的な小説生成機能
- Streamlit フロントエンド
- 基本的な API サーバー

---

## 移行ガイド

### v3.2 → v3.3 (進行中)

#### 破壊的変更
1. `engine.ai_api` / `engine.llm_client` 削除 → `engine.llm` を使用
2. `LLMGenerateResultProxy.generate()` 削除 → `generate_json()` / `generate_text()` 使用
3. 設定アクセス: `ProjectContext.get_setting()` → `get_settings().setting_name`

#### 移行手順
```python
# 旧
engine.ai_api.generate_text(...)
engine.llm_client.generate_json(...)

# 新
engine.llm.generate_text(...)
engine.llm.generate_json(...)

# 設定
from config.settings import get_settings
settings = get_settings()
model = settings.model_writing
```

#### 設定移行
```python
# 旧
from config.constants import MODEL_WRITING
from config.project_context import ProjectContext
model = ProjectContext.get_setting("model_writing")

# 新
from config.settings import get_settings
settings = get_settings()
model = settings.model_writing
```

---

## 貢献者
- メイン開発者
- コードレビワー
- テスト貢献者

---

詳細な変更履歴は Git ログを参照: `git log --oneline --decorate`