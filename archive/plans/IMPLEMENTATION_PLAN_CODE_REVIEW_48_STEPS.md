# 覇権小説エンジン v3.3 - コードレビュー改善実装計画書（48ステップ版）

## 概要

`CODE_REVIEW_DETAILED.md` および直前のコードレビューセッションで特定された改善項目を、**低性能 LLM でも実装可能な 48 の小さなステップ**に分割した詳細計画書です。

### 目的
- **保守性・拡張性・型安全性・テスタビリティ** の向上
- **技術的負債** の段階的解消
- **大規模リファクタリング** の安全な実施

### スケジュール概要（合計 8-10 スプリント）
| Phase | ステップ | 期間 | 重点 |
|-------|---------|------|------|
| **Phase 1 (Critical)** | 1-12 | 2-3スプリント | 循環依存解消・テスト修正・マジック値外部化 |
| **Phase 2 (High)** | 13-24 | 2-3スプリント | モジュール分割・型安全化 |
| **Phase 3 (Medium)** | 25-36 | 2スプリント | 設定一元化・観測性・パフォーマンス |
| **Phase 4 (Low)** | 37-48 | 2スプリント | ドキュメント・テスト戦略・品質ゲート |

### 完了基準（全 Phase 共通）
- mypy strict エラー数: **現状から 50% 以上削減**
- テスト成功率: **95% 以上**
- Ruff 重大エラー: **0 件維持**
- カバレッジ: **80% 以上**
- 既存機能リグレッション: **0 件**

---

## Phase 1: Critical 改善（最優先・ステップ1-12）

**目標**: 即時対応が必要な Critical 項目をすべて解消する

---

### Step 1: 現状把握 - `UltimateHegemonyEngine` の `_legacy` 依存箇所の完全調査

**目的**: 影響範囲を正確に把握する
**作業内容**:
- `src/backend/engine.py` を全文読解
- `_legacy_dep()` メソッドの全呼び出し箇所を grep
- 各 `@property`（`planner`, `writer`, `pm`, `ctx_mgr`, `formatter`, `validator`, `auditor`, `narrative`, `critique`, `marketing`, `bible_agent`, `plot_agent`, `style_rag`）の使用箇所を `rg "_legacy_dep"` で列挙
- 影響を受けるファイル一覧と呼び出し回数をメモ

**完了基準**: 影響範囲一覧（ファイルパス:行番号 + 依存名）を `proposals/legacy_deps_inventory.md` に作成

---

### Step 2: 現状把握 - `AppContainer2` での `engine` プロバイダ定義の確認

**目的**: DI コンテナでの engine 注入経路を理解する
**作業内容**:
- `src/core/container/app.py` の `engine` プロバイダ定義を読む
- `engine_facade` プロバイダとの関係を整理
- 現状の依存注入が `_legacy` 経由なのか直接注入なのか確認
- `tests/unit/test_container.py` で `engine` プロバイダのテスト方法を確認

**完了基準**: 注入経路図（ASCII 図）をメモとして作成

---

### Step 3: 設計 - `UltimateHegemonyEngine` 新コンストラクタ仕様

**目的**: リファクタ後のコンストラクタシグネチャを確定する
**作業内容**:
- `_legacy` 経由で取得している全依存（12 個）を明示的コンストラクタ引数として定義
- 各引数の型ヒントを確定（既存クラスから型取得）
- デフォルト値を `None` とし、後方互換のため `**legacy` も残すが `DeprecationWarning` を発行
- 命名規則を統一（`snake_case`、意味のある名前）

**完了基準**: 新仕様の docstring + メソッドシグネチャを `proposals/engine_refactor_spec.md` に記述

---

### Step 4: 実装 - `UltimateHegemonyEngine` 新コンストラクタの実装

**目的**: 12 個の依存を明示的に受け取る新コンストラクタを実装する
**作業内容**:
- `src/backend/engine.py` の `__init__` を修正
- 全依存を明示的に受け取る（`api_key`, `repo`, `db`, `llm`, `cooldown`, `plot_service`, `planner`, `writer`, `pm`, `ctx_mgr`, `formatter`, `validator`, `auditor`, `narrative`, `critique`, `marketing`, `bible_agent`, `plot_agent`, `style_rag`）
- `_legacy` 辞書は残すが `DeprecationWarning` を発火
- 型ヒントをすべて明示（`Optional[T] = None`）

**完了基準**: クラスインスタンス化が新形式で成功し、`mypy --strict` でエラーが出ない

---

### Step 5: 修正 - `_legacy_dep` プロパティ群の段階的廃止準備

**目的**: 各 `@property` を新属性アクセスに変更する準備
**作業内容**:
- `_legacy_dep` 経由の全 `@property` を新属性（直接 `self.planner` など）に置換
- ただし**まだ `_legacy` 経由でも動作する**よう、新属性が未設定なら `_legacy_dep` にフォールバック
- `ai_api` と `llm_client` の `FutureWarning` は維持（後方互換）

**完了基準**: 全プロパティが新属性として動作し、既存テストがすべて通る

---

### Step 6: 修正 - `AppContainer2.engine` プロバイダの全依存注入

**目的**: DI コンテナから新コンストラクタに必要な全依存を渡す
**作業内容**:
- `src/core/container/app.py` の `engine` プロバイダ定義を修正
- 全 12 個の依存を `providers.DelegatedFactory` または直接注入で渡す
- 既存の `engine_facade` 経由の呼び出しも同様に更新
- `tests/unit/test_container.py` の fixture を更新

**完了基準**: `AppContainer2.engine()` が新コンストラクタで完全動作

---

### Step 7: テスト - 単体テスト追加（新エンジンコンストラクタ）

**目的**: 新コンストラクタの単体テストを追加
**作業内容**:
- `tests/unit/test_engine_init.py` を新規作成
- 全依存を渡した場合、`None` を渡した場合の両方でテスト
- `DeprecationWarning` 発火テストも追加
- 既存テスト `tests/unit/test_refactoring.py` も更新

**完了基準**: 新規テスト 5 件以上すべて PASS、既存テストも PASS 維持

---

### Step 8: 修正 - テスト環境エラー修正（`prometheus_client` 未インストール）

**目的**: 即時対応可能なテストエラーを解消する
**作業内容**:
- `requirements.txt` を確認し `prometheus-client` が含まれているか確認
- 含まれていなければ最新版を追加（`prometheus-client>=0.19.0`）
- `pip install -r requirements.txt` で再インストール
- `tests/test_api_integration.py` の collection エラーが消えるか確認

**完了基準**: `pytest tests/test_api_integration.py --collect-only` がエラーなしで完走

---

### Step 9: 修正 - テスト環境エラー修正（Huey SqliteStorage パス）

**目的**: `unable to open database file` エラーを解消する
**作業内容**:
- `src/backend/worker_config.py` の `DB_PATH` 定義を確認
- 相対パスが問題なら `tmp_path` または環境変数化
- テスト用 fixture で一時ディレクトリを使うよう修正
- `tests/test_background_worker.py` を再実行

**完了基準**: `pytest tests/test_background_worker.py` がエラーなしで collection できる

---

### Step 10: 修正 - かんたんモードマジック値外部化

**目的**: `src/easy_mode/pipeline.py` のハードコード値をプリセット YAML へ移動
**作業内容**:
- `src/presets/<genre>.yaml` に `episode_structure` セクションを追加
  - 例: `humiliation_ep: 2`, `trigger_ep: 3`, `musou_start_ep: 4`, `final_ep: 8`, `tension_threshold: 75`
- 全 9 ジャンル分の YAML を整備（`zarma`, `aku_reijo`, `cheat_tensei`, `slow_life`, `dungeon_admin`, `modern_cheat`, `ts_tensei`, `vrmmo`, `loop`）
- `pipeline.py` の `_generate_bible` で `preset.get("episode_structure", {})` から値を取得
- デフォルト値は `default_preset.yaml` に集約

**完了基準**: コード上からマジック値が消え、プリセット変更で挙動が変わる

---

### Step 11: テスト - マジック値外部化の回帰テスト

**目的**: プリセット変更が正しく反映されることを検証
**作業内容**:
- `tests/test_preset_episode_structure.py` を新規作成
- 各ジャンルでプリセット読込 → 期待値チェック
- カスタムプリセット（テスト用 YAML）でオーバーライドが効くか確認
- 既存 `tests/test_phase1_preset_integration.py` も更新

**完了基準**: 全 9 ジャンル + カスタム 1 件 = 10 テストが PASS

---

### Step 12: 動作確認 - Phase 1 全体のスモークテスト

**目的**: Phase 1 のすべての修正が本番同等環境で動作することを確認
**作業内容**:
- `mypy src/` を実行しエラー数が **50% 以上削減** されたか確認
- `pytest tests/ -x` で全テスト実行（Skip 除く）
- `ruff check src/` で重大エラー 0 件維持を確認
- `coverage report --fail-under=80` でカバレッジ確認
- README の `v3.3` セクションに変更点を追記

**完了基準**: すべての品質ゲートが PASS

---

## Phase 2: High 改善（ステップ13-24）

**目標**: 巨大モジュールの分割と型安全性の向上

---

### Step 13: 現状把握 - `pipeline.py` の関数/メソッド・依存関係の完全調査

**目的**: 分割設計のための影響範囲調査
**作業内容**:
- `src/easy_mode/pipeline.py` の全メソッド（30 個以上）を列挙
- 各メソッドの行数・複雑度・依存関係を表にまとめる
- 外部依存（`engine`, `preset`, `spice_guard`, `llm`）と内部依存を分離
- メソッドをグルーピング（生成系・監査系・リライト系・進捗系・ヘルパー）

**完了基準**: `proposals/pipeline_split_design.md` にグルーピング図を作成

---

### Step 14: 設計 - `pipeline.py` の分割アーキテクチャ確定

**目的**: 新ディレクトリ構造と各モジュールの責務を明確化
**作業内容**:
- 新構造を設計:
  ```
  src/easy_mode/
    pipeline.py           # オーケストレーション専用（200行以下目標）
    bible_generator.py    # _generate_bible, _parse_bible, _fallback_bible
    plot_generator.py     # _generate_plot_outline, _interpolate_tension, _select_plot_pattern
    episode_writer.py     # _write_episode, _build_writing_prompt
    episode_auditor.py    # _audit_episode
    episode_rewriter.py   # _rewrite_episode, _inject_spice_markers
    series_finalizer.py   # _finalize_series, _finalize_result
    progress_reporter.py  # _report_progress
    presets/
      loader.py           # 既存
  ```
- 各モジュールの公開 API（関数シグネチャ）を定義

**完了基準**: 設計書（ASCII クラス図付き）を `proposals/pipeline_split_design.md` に記述

---

### Step 15: 実装 - `bible_generator.py` の抽出

**目的**: Bible 生成ロジックを独立モジュール化
**作業内容**:
- 新ファイル `src/easy_mode/bible_generator.py` を作成
- `EasyModeBibleGenerator` クラスを定義（`generate(bible_template, preset_vars) -> dict`）
- `pipeline.py` から `_generate_bible`, `_parse_bible`, `_fallback_bible` を移動
- 単体テスト `tests/test_bible_generator.py` を作成

**完了基準**: 新モジュール単体テストが PASS、`pipeline.py` が約 50 行削減

---

### Step 16: 実装 - `plot_generator.py` の抽出

**目的**: プロット生成ロジックを独立モジュール化
**作業内容**:
- 新ファイル `src/easy_mode/plot_generator.py` を作成
- `EasyModePlotGenerator` クラスを定義（`generate(bible, target_episodes, tension_curve) -> list[dict]`）
- `pipeline.py` から `_generate_plot_outline`, `_interpolate_tension`, `_select_plot_pattern` を移動
- テンション補間の単体テスト（境界値・空リスト・単調増加）を充実

**完了基準**: テンション補間テストで 10 ケース以上 PASS

---

### Step 17: 実装 - `episode_writer.py` の抽出

**目的**: 執筆ロジックを独立モジュール化
**作業内容**:
- 新ファイル `src/easy_mode/episode_writer.py` を作成
- `EasyModeEpisodeWriter` クラスを定義
- プリセット注入（`style_dna`, `hooks`, `erotic_rules`）をコンストラクタで受け取る
- プロンプト構築と LLM 呼び出しを分離（テスタビリティ向上）

**完了基準**: 既存テスト `tests/test_episode_writer.py` が PASS 維持

---

### Step 18: 実装 - `episode_auditor.py` と `episode_rewriter.py` の抽出

**目的**: 監査・リライトロジックを独立モジュール化
**作業内容**:
- 新ファイル `src/easy_mode/episode_auditor.py` を作成
- `EasyModeEpisodeAuditor` クラスを定義（`audit(content, context) -> AuditResult`）
- 新ファイル `src/easy_mode/episode_rewriter.py` を作成
- `EasyModeEpisodeRewriter` クラスを定義（`rewrite(content, improvements, spice_elements) -> str`）
- スコア正規化ロジック（1000点満点 → 100点満点）を `AuditResult` クラスに集約

**完了基準**: 監査とリライトが独立してテスト可能

---

### Step 19: 実装 - `pipeline.py` のリファクタリング（オーケストレーション専用化）

**目的**: `pipeline.py` を純粋な制御フローのみに簡素化
**作業内容**:
- `src/easy_mode/pipeline.py` を全面書き換え
- 各サブモジュールを DI として受け取り、`run()` メソッドで順次呼び出す
- 進捗報告・キャンセル・リトライ制御に集中
- 200 行以下を目標（現在 593 行 → 60% 削減）

**完了基準**: `pipeline.py` が 200 行以下、すべての Phase 1-3 統合テストが PASS

---

### Step 20: 現状把握 - `spice_guard.py` の分割ポイント調査

**目的**: パターン定義・抽出・マーカー操作の責務分離
**作業内容**:
- `src/easy_mode/spice_guard.py` のメソッド・クラスを列挙
- パターン定義（`UNIVERSAL_PATTERNS`, `GENRE_PATTERNS`）と抽出ロジックを分離
- マーカー注入・除去とリライトプロンプト構築を分離
- 単体テスト `tests/test_spice_guard_*.py` の影響範囲を確認

**完了基準**: 分割設計図を `proposals/spice_guard_split_design.md` に作成

---

### Step 21: 実装 - `spice_guard/pattern_registry.py` の抽出

**目的**: パターン定義を一元管理
**作業内容**:
- 新ディレクトリ `src/easy_mode/spice_guard/` を作成
- `pattern_registry.py` を新規作成（`UniversalPatterns`, `GenrePatterns`, `CompiledPatternCache`）
- `UNIVERSAL_PATTERNS` と `GENRE_PATTERNS` をこのモジュールへ移動
- 正規表現の事前コンパイルを `CompiledPatternCache` クラスに集約

**完了基準**: パターンマッチング速度が **20% 以上向上**（ベンチマーク測定）

---

### Step 22: 実装 - `spice_guard/extractor.py` と `marker.py` の抽出

**目的**: 抽出・マーカー操作を独立モジュール化
**作業内容**:
- `src/easy_mode/spice_guard/extractor.py` を作成（`SpiceExtractor` クラス）
- `src/easy_mode/spice_guard/marker.py` を作成（`SpiceMarkerInjector`, `SpiceMarkerCleaner`）
- `src/easy_mode/spice_guard.py` はファサードとして薄く残す（後方互換）
- 各モジュールの単体テストを追加

**完了基準**: SpiceGuard 関連テスト 20 件以上すべて PASS

---

### Step 23: 修正 - 型安全性の穴修正（`llm_gateway.py`）

**目的**: `Any` 型を排除して型安全性を向上
**作業内容**:
- `src/core/llm_gateway.py` の `purpose_or_request: Any` を `Union[str, LLMRequestOptions]` に修正
- `generate()` メソッドは削除（既に `NotImplementedError` なので完全削除）
- `overload` デコレータで `generate_json`/`generate_text` の型シグネチャを明示
- mypy で確認

**完了基準**: `mypy --strict src/core/llm_gateway.py` でエラー 0 件

---

### Step 24: 動作確認 - Phase 2 全体のスモークテスト

**目的**: Phase 2 のすべての修正が本番同等環境で動作することを確認
**作業内容**:
- `mypy src/` を実行
- `pytest tests/ -x` で全テスト実行
- `coverage report --fail-under=80` でカバレッジ確認
- `pipeline.py` と `spice_guard.py` の行数削減目標達成確認

**完了基準**: すべての品質ゲートが PASS、`pipeline.py` < 200行、`spice_guard.py` < 200行

---

## Phase 3: Medium 改善（ステップ25-36）

**目標**: 設定管理・観測性・パフォーマンスの改善

---

### Step 25: 現状把握 - 設定管理ファイル全体の棚卸し

**目的**: 設定の重複・分散状況を把握
**作業内容**:
- `config/constants.py`, `config/project_context.py`, `schemas/config.py`, `GlobalConfigModel`, 環境変数の使用箇所を全て grep
- 同じ設定値が複数箇所に定義されていないか確認
- 各設定の参照回数とライフサイクルを表にまとめる

**完了基準**: 設定一覧表を `proposals/config_consolidation.md` に作成

---

### Step 26: 設計 - `pydantic-settings` ベースの統一設定クラス設計

**目的**: 単一 `Settings` クラスへの統合設計
**作業内容**:
- 新ファイル `config/settings.py` の設計
- `pydantic-settings.BaseSettings` を継承した `AppSettings` クラスを定義
- 全設定値（環境変数 + YAML + 定数）を統合管理
- セクション分け: `DatabaseConfig`, `RedisConfig`, `LLMConfig`, `AuthConfig`, `ObservabilityConfig`, `RateLimitConfig`

**完了基準**: 設定クラス仕様を `proposals/config_consolidation.md` に記述

---

### Step 27: 実装 - `config/settings.py` の実装

**目的**: 統一設定クラスを実装
**作業内容**:
- `config/settings.py` を新規作成
- `AppSettings(BaseSettings)` を定義
- 環境変数プレフィックス: `KAKU_`（例: `KAKU_DATABASE_URL`, `KAKU_GEMINI_API_KEY`）
- `.env.example` を新形式に合わせて更新
- 既存コードからの段階的移行用ヘルパー関数 `get_legacy_setting()` を提供

**完了基準**: `AppSettings().database_url` などで値取得できる

---

### Step 28: 移行 - `constants.py` から `settings.py` への段階的移行

**目的**: 既存コードの新設定クラスへの置き換え
**作業内容**:
- `src/backend/server.py` から `_LONG_RUNNING_TIMEOUT_SEC` 等の定数参照を `settings.timeouts.long_running_sec` に置換
- 1 ファイルずつ慎重に移行（一度に全部変更しない）
- 各置換後にテスト実行
- 移行済み定数には `# DEPRECATED: use config.settings.timeouts.*` コメントを追加

**完了基準**: `constants.py` の参照箇所が **30% 以上削減**

---

### Step 29: 移行 - `GlobalConfigModel` と `project_context.py` の統合

**目的**: 残存する設定クラスを `AppSettings` に統合
**作業内容**:
- `schemas/config.GlobalConfigModel` を `AppSettings` に統合
- `config/project_context.GlobalConfig` をラッパーとして残しつつ、内部で `AppSettings` を使用
- `InfraContainer.config` プロバイダを `AppSettings` ベースに更新

**完了基準**: `AppContainer2` 起動時にエラーが出ない

---

### Step 30: テスト - 設定管理の統合テスト

**目的**: 新設定クラスの動作を検証
**作業内容**:
- `tests/test_settings.py` を新規作成
- 環境変数からの読込テスト
- デフォルト値のテスト
- オーバーライド（`.env` ファイル）のテスト
- 型バリデーション（不正値の拒否）テスト

**完了基準**: 設定テスト 15 件以上すべて PASS

---

### Step 31: 修正 - 非同期セマフォの遅延生成化

**目的**: `asyncio.Semaphore` のループ生成エラーを解消
**作業内容**:
- `src/core/container/infra.py` の `concurrency_semaphore` を `providers.Factory` に変更
- 初回呼び出し時に `asyncio.get_running_loop()` を確認
- ファクトリ関数で遅延生成
- 既存の `tests/unit/test_async_utils.py` を更新

**完了基準**: `pytest tests/unit/test_async_utils.py` が PASS

---

### Step 32: 修正 - SpiceGuard の正規表現パフォーマンス改善

**目的**: 長文での抽出速度を向上
**作業内容**:
- `src/easy_mode/spice_guard/extractor.py` で `re.compile` 済みパターンをキャッシュ
- キーワード検索を `set` で事前ルックアップ
- 重複する `finditer` を `findall` で先にチェック
- ベンチマークテスト `tests/perf/test_spice_guard_bench.py` を作成

**完了基準**: 10,000文字のテキストで抽出が **100ms 以下**、メモリ使用量 **20% 削減**

---

### Step 33: 修正 - エラーハンドリングの不統一解消（pipeline.py）

**目的**: 例外握りつぶしを例外ラップに変更
**作業内容**:
- `src/core/exceptions.py` に `BibleGenerationError`, `EpisodeWritingError`, `AuditFailureError` を追加
- `pipeline.py` の `except Exception` ブロックを新例外でラップ
- フォールバック使用時は `metadata["fallback_reason"]` に詳細を記録
- ログレベルを `WARNING` から構造化ログ（`extra={"error_code": ...}`）に

**完了基準**: 例外ログから失敗原因が追跡可能

---

### Step 34: 観測性 - OpenTelemetry 自動計装の強化

**目的**: 主要パスを自動的にトレース
**目的**: （再掲）
**作業内容**:
- `src/backend/server.py` の startup に OpenTelemetry 自動計装を追加（FastAPI, SQLAlchemy, Redis, ChromaDB）
- `src/easy_mode/pipeline.py` の主要メソッドにカスタム span を追加
- `LLMGenerateResultProxy.generate_json`/`generate_text` に span 追加
- トレースサンプリングレートを `0.1`（10%）に設定（本番）

**完了基準**: `/api/easy_mode/generate` 実行時にトレース ID で全工程が可視化される

---

### Step 35: 観測性 - メトリクス命名規約の統一

**目的**: Prometheus メトリクス名の標準化
**作業内容**:
- `src/backend/observability/metrics.py` のメトリクス名を再確認
- 命名規約: `{namespace}_{subsystem}_{name}_{unit}`（例: `kaku_http_requests_total`, `kaku_llm_tokens_total`）
- ラベル命名: `endpoint`, `method`, `status`, `model`, `genre` 等を統一
- 既存カスタムメトリクスを段階的にリネーム（後方互換のため alias 維持）

**完了基準**: Prometheus 出力の `# HELP` と `# TYPE` が規約通り

---

### Step 36: 動作確認 - Phase 3 全体のスモークテスト

**目的**: Phase 3 のすべての修正が本番同等環境で動作することを確認
**作業内容**:
- `mypy src/` を実行
- `pytest tests/ -x` で全テスト実行
- 設定移行による既存 API 互換性確認
- 観測性強化後のトレース・メトリクス出力をサンプル確認

**完了基準**: すべての品質ゲートが PASS、後方互換性維持

---

## Phase 4: Low 改善（ステップ37-48）

**目標**: ドキュメント・テスト戦略・品質ゲートの整備

---

### Step 37: ドキュメント - アーキテクチャ図（C4 モデル）作成

**目的**: システム構造の可視化
**作業内容**:
- `docs/architecture/` ディレクトリを作成
- `01-system-context.md`（システムコンテキスト図）
- `02-containers.md`（コンテナ図）
- `03-components.md`（コンポーネント図）
- `04-code.md`（コードレベルのクラス図）
- Mermaid 形式で記述（README でレンダリング可能）

**完了基準**: 4 つの C4 図が完成し、README からリンク

---

### Step 38: ドキュメント - シーケンス図（主要ユースケース）

**目的**: 主要フローの可視化
**作業内容**:
- `docs/architecture/sequences/` ディレクトリ作成
- 以下のシーケンス図を Mermaid 形式で作成:
  - `01-easy-mode-generation.md`（かんたんモード生成フロー）
  - `02-episode-rewrite.md`（エピソードリライトフロー）
  - `03-bible-sync.md`（Bible 同期フロー）
  - `04-spice-guard.md`（SpiceGuard 動作フロー）

**完了基準**: 4 つのシーケンス図が完成

---

### Step 39: ドキュメント - データフロー図

**目的**: データの流れを可視化
**作業内容**:
- `docs/architecture/data-flow.md` を作成
- Bible → Plot → Episode のデータ変換フローを記述
- DB・ChromaDB・Redis 間のデータ移動を明示
- 機密情報（API キー、個人情報）の取り扱いも記述

**完了基準**: データフロー図が完成

---

### Step 40: ドキュメント - 開発者ガイド

**目的**: 新規開発者のオンボーディング資料
**作業内容**:
- `docs/DEVELOPER_GUIDE.md` を新規作成
- セクション: プロジェクト構成 / 開発環境セットアップ / テスト実行 / デバッグ / コード規約 / コントリビューションフロー
- `AGENTS.md` との整合性確保

**完了基準**: ガイド完成、新規開発者が 1 時間でセットアップ完了可能

---

### Step 41: テスト戦略 - Testcontainers 統合テスト整備

**目的**: 実環境に近い統合テストの実現
**作業内容**:
- `tests/integration/` に Testcontainers ベースのテストを追加
- PostgreSQL, Redis, ChromaDB のコンテナを pytest-xdist と組み合わせて並列実行
- `tests/integration/conftest.py` にフィクスチャ追加
- 既存 `tests/integration/test_db.py` を Testcontainers ベースに更新

**完了基準**: Testcontainers 統合テスト 5 件以上追加、すべて PASS

---

### Step 42: テスト戦略 - E2E テスト自動化（Playwright 検討）

**目的**: フロントエンド含む E2E テスト自動化
**作業内容**:
- Playwright 導入可否を `proposals/e2e_evaluation.md` にまとめる
- 導入する場合: `tests/e2e/` ディレクトリ作成、主要フロー 3 件を実装
- 導入しない場合: 既存の手動 E2E チェックリストを `docs/MANUAL_E2E.md` に整備

**完了基準**: E2E テスト戦略決定文書化

---

### Step 43: テスト戦略 - ミューテーションテスト導入

**目的**: テストの品質を定量評価
**作業内容**:
- `mutmut` または `cosmic-ray` を導入
- `pyproject.toml` に設定追加
- 主要モジュール（`src/easy_mode/`, `src/backend/engine.py`）にミューテーション実行
- カバレッジ目標: **60% 以上**

**完了基準**: ミューテーションスコア 60% 以上

---

### Step 44: 品質ゲート - pre-commit フック整備

**目的**: コミット時の自動品質チェック
**作業内容**:
- `.pre-commit-config.yaml` を確認・更新
- 追加フック: `mypy`, `ruff`, `bandit`（セキュリティ）, `vulture`（デッドコード検出）, `gitleaks`（シークレット検出）
- CI と pre-commit の設定重複を整理
- フック実行時間測定（5分以内目標）

**完了基準**: pre-commit フックが 5 分以内に完走

---

### Step 45: 品質ゲート - CI パイプライン改善

**目的**: CI での品質チェック強化
**作業内容**:
- `.github/workflows/ci.yml` を確認
- 追加ジョブ: `mutation-test`, `dependency-audit`（`pip-audit`）, `code-complexity`（`xenon`）
- ジョブ並列化による高速化
- キャッシュ戦略の見直し（`pip`, `node_modules`, `chroma_db`）
- バッジ追加（`README.md` 更新）

**完了基準**: CI 実行時間が 10 分以内、品質チェック漏れ 0 件

---

### Step 46: レガシーコード削除 - 廃止予定プロパティの完全削除

**目的**: `FutureWarning` 付きプロパティの完全削除
**作業内容**:
- `src/backend/engine.py` の `ai_api`, `llm_client` を削除（v3.3 で 1 バージョン警告期間）
- `src/backend/server.py` 内の互換性コードを削除
- 削除前に `kilo_local_recall` で過去の使用状況を確認
- CHANGELOG に削除を記載

**完了基準**: レガシープロパティ参照が 0 件、テスト全 PASS

---

### Step 47: ドキュメント - CHANGELOG 整備

**目的**: バージョン履歴の整備
**作業内容**:
- `CHANGELOG.md` を新規作成
- v3.3, v3.4, v3.5（予定）のセクション
- 各バージョンで追加・変更・削除された機能を箇条書き
- 移行ガイドへのリンク

**完了基準**: CHANGELOG が v3.0 から全バージョン網羅

---

### Step 48: 最終動作確認 - Phase 4 全体 + プロジェクト全体

**目的**: 48 ステップすべての完了確認とリリース判定
**作業内容**:
- `mypy src/` エラー数: 0 件
- `pytest tests/ --cov=src --cov-fail-under=80` 全 PASS
- `ruff check src/` 重大エラー 0 件
- `bandit -r src/` セキュリティ問題 0 件（High のみ）
- `vulture src/` デッドコード 0 件
- `mutmut run` スコア 60% 以上
- `pip-audit` 脆弱性 0 件（High/Critical）
- CI パイプライン全 PASS（10分以内）
- README.md 更新（v3.4 セクション追加）

**完了基準**: すべての品質ゲートが PASS、リリース判定 OK

---

## 📊 進捗管理

### 各ステップの完了基準テンプレート
```markdown
- [ ] 作業内容すべて完了
- [ ] 単体テスト PASS（新規追加分）
- [ ] 既存テスト PASS（リグレッション 0 件）
- [ ] `mypy --strict` で新規エラー 0 件
- [ ] `ruff check` で新規エラー 0 件
- [ ] 該当ドキュメント更新
- [ ] PR 作成・レビュー・main マージ
```

### 各 Phase 終了時の振り返りチェックリスト
```markdown
- [ ] Phase 目標達成
- [ ] メトリクス目標達成（行数削減、エラー削減等）
- [ ] ドキュメント更新
- [ ] 関係者レビュー
- [ ] 次 Phase の前提条件クリア
```

---

## 🔗 関連ドキュメント

- [CODE_REVIEW_SUMMARY.md](CODE_REVIEW_SUMMARY.md) - コードレビューサマリ
- [CODE_REVIEW_DETAILED.md](CODE_REVIEW_DETAILED.md) - 詳細コードレビュー
- [README.md](README.md) - プロジェクト概要
- [IMPLEMENTATION_PLAN_24_STEPS.md](IMPLEMENTATION_PLAN_24_STEPS.md) - 既存計画書（参考）

---

## 📝 変更履歴

| 日付 | バージョン | 変更内容 | 担当 |
|------|-----------|----------|------|
| 2026-08-16 | v1.0 | 初版作成（48 ステップ） | Kilo |
