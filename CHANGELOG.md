# 覇権小説エンジン - CHANGELOG

すべての注目すべき変更を記録します。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づき、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に従います。

## [Unreleased]

### Added
- 統一設定クラス `config.settings.Settings` (pydantic-settings.BaseSettings)
- 全依存を明示的に注入する `UltimateHegemonyEngine` コンストラクタ
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
- カスタム例外クラス追加 (`BibleGenerationError`, `EpisodeWritingError`, 等)
- Testcontainers 統合テスト基盤
- Playwright E2E テスト戦略ドキュメント
- ミューテーションテスト導入ガイド (`mutmut`)
- Pre-commit フック整備 (ruff, mypy, bandit, vulture, xenon, gitleaks, pip-audit)
- CI パイプライン全面改善 (並列化、キャッシュ、品質ゲート)

### Changed
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

### Removed
- `UltimateHegemonyEngine.ai_api` プロパティ (FutureWarning 期間終了)
- `UltimateHegemonyEngine.llm_client` プロパティ (FutureWarning 期間終了)
- `llm_gateway.py` の `generate()` メソッド (NotImplementedError だったもの)

### Fixed
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
- コードレビュワー
- テスト貢献者

---

詳細な変更履歴は Git ログを参照: `git log --oneline --decorate`