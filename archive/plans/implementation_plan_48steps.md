# 官能特化型サブエージェント実装計画：48ステップ

## 前提

- **対象**: `streamlit_app/app.py` を含むツール群
- **問題**: 多くのスタブ（Stub）モジュールが未実装
- **前提**: Python 3.11+, Pydantic v2, Streamlit, asyncio
- **方式**: スタブを段階的に実装修正へ置き換える48の反復ステップ

---

## Phase 1: 基盤死活監視とログ (Step 1-8)

### Step 1: `src/health_check.py` を実装修正
- Stub 状態 (`return True`) を実際の Gemini API 疎通チェックに置き換える
- `validate_api_key_async()` 関数も実装
- `ensure_backend_available()` で Streamlit サーバー ↔ バックエンド死活監視

### Step 2: `config/logging_config.py` 確認・整備
- `setup_logging()` の logger 設定確認（JSON形式対応）
- `src/utils/errors.py` の `AppErrorHandler` 実装確認

### Step 3: `src/landing.py` Stub 置換
- インポート元 `src.landing` → `streamlit_app.landing` が重複参照
- 実体である `streamlit_app/landing.py` を確認して実装修正
- API キー未入力時のランディングページ表示を完成

### Step 4: `src/sidebar.py` Stub 置換
- `streamlit_app/sidebar.py` が `from src.state` を参照しているが `src/state.py` は存在しない
- `from streamlit_app.state import get_session, UIStateStore, SessionManager` に修正
- 作品一覧・モード切替・API キー入力UIを完成

### Step 5: Streamlit インポートパス統一
- `app.py` 内で `from src.health_check import ...` となっているのを `from streamlit_app.health_check import ...` に統一
- または `src/health_check.py` を実装修正して import 整合性を確保

### Step 6: `config/file_watcher.py` 実装
- 設定ファイル変更監視用クラス `ConfigFileWatcher`
- JSON/YAML 設定変更時の自動リロード機能

### Step 7: ログ出力の動作検証
- 各スタックレイヤー (app → service → agent) でのログ垂れ流し確認
- `logger.info / warning / error` が正しく伝わるか検証

### Step 8: Streamlit サーバー起動確認
- `streamlit run streamlit_app/app.py` がエラーなく起動することを確認
- サイドバー・Landing 表示の描画確認

---

## Phase 2: エンジンサービスとLLM接続 (Step 9-16)

### Step 9: `streamlit_app/engine_service.py` 実装修正
- Stub (`return EngineService()`) を Gemini API クライアントとして実装
- `api_key` 単位でのインスタンスキャッシュ (싱글톤)
- `get_all_books()`, `get_book_details(id)`, `delete_book(id)` 実装
- API: Gemini API 向け `src/llm/` モジュールの利用

### Step 10: `src/llm/` モジュールの整備
- `src/llm/gemini_client.py` - Gemini API 呼び出しラッパー
- `generate_json()`, `generate_text()` メソッド実装
- `src/llm/model_router.py` - モデル選択ロジック

### Step 11: `src/services/llm_service.py` 実装
- LLM 呼び出し высок Level Service
- リトライ機構 (`src/services/retry_decorator.py`) との統合
- レートリミット対応 (`src/core/rate_limiter.py`)

### Step 12: API キー検証パイプライン完成
- Sidebar からの API キー入力 → `validate_api_key_async` → 結果通知
- `is_api_key_valid` フラグを `UIStateStore` に正しく反映
- 失敗時のエラーメッセージ表示

### Step 13: `src/backend/` API クライアント実装
- `src/backend/engine_api_client.py` - サーバーサイド API 呼出
- `src/backend/sanitizer.py` - 出力サニタイズ (AtmosphereGenerator, ContentValidator, TonePerfector, OutputSanitizer)

### Step 14: LLM レスポンス構造体 (Pydantic) 確認
- `src/models/base.py` の `GenerateResult`
- `src/models/db.py` - BookDbModel, ChapterDbModel 等
- `src/models/audit.py` - LogicalAuditResult, HegemonyAuditResult 等

### Step 15: `src/core/llm_gateway.py` 実装
- 複数の LLM プロバイダーを抽象化するゲートウェイ
- Gemini / GPT 等のprovider切替機能

### Step 16: EngineService と LLM クライアントの結合テスト
- API キー有効時の書籍一覧取得
- API キー無効時のエラー処理

---

## Phase 3: セッション管理と状態管理 (Step 17-24)

### Step 17: `schemas/app_state.py` 完成確認
- `AppStateModel`, `AppRuntimeState` の全フィールド確認
- `WizardState`, `TokenStats` の整合性チェック

### Step 18: `streamlit_app/state.py` の実装修正 (その1)
- `SessionManager._get_storage_path()` - `streamlit/runtime/scriptrunner` context 利用確認
- `get_state()`, `save_state()` - ファイル永続化の動作確認

### Step 19: `streamlit_app/state.py` の実装修正 (その2)
- `UIStateStore.subscribe()` メカニズムの実装確認
- `active_job` 変更時の `st.toast()` 通知が正しく動くか検証
- 他のイベント (backend_connection_error 等) への対応拡張

### Step 20: `streamlit_app/state.py` の実装修正 (その3)
- `get_api_key_input()`, `set_api_key_input()` メソッド実装
- `get_runtime()`, `get_runtime_value()` メソッド確認
- フラグメントバージョン管理 (`fragment_versions`) の用途明確化

### Step 21: `src/core/state/` の実装
- `src/core/state/agent_state.py` - エージェント固有の状態管理
- `src/core/state/workflow_state.py` - ワークフロー状態管理
- エージェント間の状態共有機構

### Step 22: `src/services/state_manager.py` 実装
- 分散状態管理 (ファイル + メモリ)
- 状態変更のトランザクション的扱いをサポート
- `save_state()`, `load_state()`, `reset_state()` API

### Step 23: セッション復元テスト
- ブラウザリロード後に状態 (current_book_id, app_mode 等) が復元されるか検証
- `active_job` (プロキシオブジェクト) がシリアライズ例外を発生させていないか確認

### Step 24: `UIStateStore` と `st.session_state` の完全分離検証
- UI コンポーネントが `st.session_state` に直接アクセスしていないことを確認
- 全パスが `UIStateStore` 経由になっているコードレビュー

---

## Phase 4: コアエージェント群の実装 (Step 25-34)

### Step 25: `src/agents/base.py` の強化
- `_safe_get_dict()`, `_safe_get_list()` の利用場所確認
- `_get_book_branch()` が `self.repo` 依赖の修正
- 基底クラスに共通ロガー・設定アクセスを追加

### Step 26: `src/agents/writing.py` スタブ除去
- `WritingAgent` - 小説生成 담당 агент
- `PlotterWorker` - プロット生成ワーカー
- `PipelineSentinel` - パイプライン監視
- `repo` (Repository) 依存の具体実装との接続

### Step 27: `src/agents/writing_scheduler.py` 実装
- `StreamingPlotScheduler` - プロット生成スケジューリング
- `plot_queue` (asyncio.Queue) 経由の処理
- `stop_event` によるキャンセル対応

### Step 28: `src/agents/audit.py` の実装修正
- `FastPlotScreener` - プロット快速スクリーニング
- `AbilityConsistencyChecker` - 能力整合性チェック
- `PlotIntegrityMonitor` - プロット整合性監視
- `DeAIAuditor` - AI感除去監査

### Step 29: `src/agents/planning.py` 実装
- 計画 담당 агент
- 作品全体構成の立案
- アーク (arc) 設計・ロードマップ生成

### Step 30: `src/agents/bible.py` 実装
- 世界観設定 создание агент
- `build_world_creation_prompt`, `build_mc_creation_prompt` 利用
- キャラクター設定・舞台設定の生成

### Step 31: `src/agents/debate.py` 実装
- 議論・審査 담당 агент
- 複数の案から最適解を裁定

### Step 32: `src/agents/marketing.py` 実装
- マーケティング担当 агент
-  Synopsis・キャッチコピー・表紙案生成
- `build_marketing_pack_prompt`, `build_title_generation_prompt` 利用

### Step 33: `src/agents/state_validator.py` 実装
- ワークフロー状態検証 агент
- 不整合状態检测・自動修復提案

### Step 34: `src/agents/diversity_scorer.py` 実装
- 多様性スコア算出 агент
- コンテンツの内容量・多様性を定量化

---

## Phase 5: パイプライン・サービス層 (Step 35-42)

### Step 35: `src/services/writing_pipeline.py` 完成
- `PipelineContext`, `PipelineStep` によるパイプライン設計
- `PlotReadyStep`, `PrefetchStep`, `ApplyPatchStep` の実装確認
- ステップ実行の例外處理・failed_episodes への記録

### Step 36: `src/services/bible_service.py` 実装
- 世界観情報管理サービス
- `get_latest_bible()`, `save_bible()` 等の Repository 経由アクセス

### Step 37: `src/services/plot_service.py` 実装
- プロット管理サービス
- `get_plots_between()`, `get_all_non_anchor_chapters()` 実装
- `expand_plots()` - プロット詳細展開

### Step 38: `src/services/novel_service.py` 実装
- 小説全体管理サービス
- 書籍作成・更新・削除の制御
- 話数伸長時のプロット自動生成トリガー

### Step 39: `src/services/audit_service.py` + `parallel_audit.py` 実装
- 監査サービス
- 並行監査 (parallel_audit) による処理高速化
- `LogicalAuditResult`, `HegemonyAuditResult` 生成

### Step 40: `src/services/narrative_scoring_service.py` 実装
- 叙評（ナラティブ）スコアリング
- 文体・テンポ・感情曲線の分析

### Step 41: `src/services/content_processor.py` 実装
- コンテンツ加工サービス
- アプローチ表現转换为objective表現
- 官能表現の风格调整

### Step 42: `src/services/healing_pipeline.py` 実装
- 不整合修復パイプライン
- `build_global_repair_prompt()` による自動修正

---

## Phase 6: フロントエンド・UI統合 (Step 43-48)

### Step 43: `streamlit_app/pages_config.py` 実装修正
- Stub (`return {"easy": [...], "advanced": [...]}`) を本実装に
- `get_pages()` が返す辞書のキーを `"Easy Mode"` / `"Advanced Mode"` に統一
- `st.navigation(pages[page_key])` の動的ページ構成対応

### Step 44: `streamlit_app/ui/` コンポーネント整備
- `ui/components/` の各コンポーネント実装確認
- `ui_tabs_writing.py`, `ui_tabs_planning.py`, `ui_tabs_audit.py`, `ui_tabs_marketing.py`, `ui_tabs_monitor.py`, `ui_tabs_analytics.py`
- ページнутренние タブの Streamlit コンポーネント完成

### Step 45: `streamlit_app/backend_launcher.py` 実装
- バックエンドサーバー自動起動功能
- `subprocess` でバックエンドプロセスを管理

### Step 46: `streamlit_app/event_bus.py` 実装
- アプリ内イベントバス
- `subscribe` / `publish` メカニズム
- 非同期タスクの進捗通知

### Step 47: `src/core/plugin_loader.py` + `system_plugin_loader.py` 実装
- `load_all_plugins()` の実装修正
- `PluginLoader` による動的機能ロード
- `SystemPluginLoader` によるシステムレベルプラグイン管理

### Step 48: エンドツーエンド統合テスト
- 書籍作成 → プロット生成 → 小説執筆 → 監査 → エクスポートの全流程
- UI (Streamlit) ↔ Backend API ↔ Database (SQLite) ↔ LLM (Gemini) の繋ぎ込み
- `streamlit run streamlit_app/app.py` からの完全動作確認
- テストスイート (`pytest`) の実行確認

---

## 完了条件

1. 全48ステップがエラーなく通過
2. `pytest` テストが通過 (または既知の失敗のみ)
3. `streamlit run streamlit_app/app.py` が起動し、書籍作成〜執筆〜 аудит の全程が UI から操作可能
4. ログにエラー/ワーニングがでない (設定した阀値内)
5. 型ヒント (`mypy`) による检查が通過

---

## リスク・制約

- **LLM API**: Gemini API キーが必須。実APIない場合はモック利用
- **並列処理**: `asyncio` 利用箇所は Streamlit の制約あり。バックグラウンドは `threading` 検討
- **状態永続化**: `active_job` (プロキシ) はシリアライズ不可のため `exclude` 处置済み。今後の扩展に注意
- **インポート循環**: `src/` ↔ `streamlit_app/` 間の import 循環がないか随時チェック