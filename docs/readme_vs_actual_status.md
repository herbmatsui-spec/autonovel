# AutoNovel プロジェクト精査レポート：README と実態の対比一覧表

作成日: 2026-09-24  
対象リポジトリ: AutoNovel (`herbmatsui-spec/autonovel`)

---

## 📋 概要・背景

本ドキュメントは、AutoNovel プロジェクトにおいて繰り返された改修・機能拡張・リファクタリングの結果生じた **`README.md` の記述と実際のソースコード・ファイル構成・アーキテクチャの乖離** を精査し、今後の開発・リファクタリング・ドキュメント改定の参考資料として対比表形式でまとめたものです。

---

## 📊 README と実態の対比一覧表 (Comparison Matrix)

| カテゴリ | README.md の記載内容 | 実際のコード / ファイルの状況 | 乖離・実態詳細・開発への示唆 |
| :--- | :--- | :--- | :--- |
| **バージョン** | **v5.0.3** (バッジ・本文) | `pyproject.toml`: **5.0.3**<br>`src/cli/main.py`: **5.1.0** | 統一CLIエントリポイントが `5.1.0` を名乗っており、マイナーバージョンの足並みが不整合になっています。 |
| **執筆サービス<br>(WritingService)** | 「4層圧縮統合」項で `WritingService` や `EpisodeWriter`、`EasyMode` パイプラインを直接紹介 | **`src/domain/writing/` に統合完了**<br>- `src/domain/writing/coordinator.py`<br>- `src/domain/writing/quality_loop.py`<br>- `src/domain/writing/state_guard.py` | 以前は 3 箇所に分裂していた `writing_service.py` は **`src/domain/writing/` に集約**され、旧 `src/services/writing_service.py` 等は DeprecationWarning を出す薄いシム（互換ラッパー）になっています。 |
| **エージェント基盤<br>(agent / agents)** | 単にエージェントが連携して執筆する旨の機能紹介 | **`src/agents/` に一本化**<br>- 旧 `src/agent/` は非推奨シム<br>- `src/agents/writer_agent.py`<br>- `src/agents/tool_handler.py`<br>- `src/agents/memory/` | エージェント層が `src/agents` に統合され、感情検出プロンプト (`prompts/emotion_detection.md`) やツール呼び出しハンドラー、短期/長期メモリ機構が追加されています。 |
| **プラグイン機構<br>(Plugin Registry)** | 個別の環境変数（`ENABLE_MULTIMEDIA` 等）の記載のみ | **動的プラグインシステムを導入**<br>- `src/core/plugin_registry.py`<br>- `src/interfaces/plugin.py`<br>- `src/plugins/` (multimedia, audio, social_posting) | 単なるフラグ分岐ではなく、`PluginRegistry` による動的ロード・条件付きルーティング（例: `multimedia` 無効時はルーター自体をマウントしない）アーキテクチャへと進化しています。 |
| **CLI コマンド** | `dsp-balance`, `csp-balance`, `grammar-balance` 等の個別コマンドを `pyproject.toml` やマニュアルで想定 | **統一 CLI `autonovel` が新設**<br>- `src/cli/main.py`<br>- `autonovel balance --type dsp`<br>- `autonovel export`, `init-db`, `check-env` | 個別スクリプトは互換エイリアス化され、`autonovel <subcommand>` という近代的な統一CLIインターフェースが整備されています。 |
| **知識グラフ<br>(GraphRAG / AGE)** | 「Apache AGE 未使用、pgvector/ChromaDB ベース」と記載 | **リレーショナルメモリ＋ChromaDB / pgvector に完全移行**<br>- `src/services/age_client.py` は完全廃止スタブ | `age_client.py` はダミー実装の非推奨スタブのみ残り、Apache AGE への依存は完全に排除されています。 |
| **起動・終了スクリプト** | `アプリ起動_ローカル.bat` と `アプリ停止.bat` の紹介<br>(内部で `scripts/start_local.ps1` を実行) | **実体と一致。さらに `stop_local.ps1`, `check_env.py`, `init_db.py` が追加** | Windowsローカル起動まわりはスクリプト・バッチともに整備済み。orphan プロセスの安全キル機能や事前ヘルスチェック (`check_env.py`) が強化されています。 |
| **バックエンド API ルーター** | 基本機能（執筆・設定・エクスポート・GraphRAG等）の紹介 | **多数の商用・高度ルーターが追加**<br>- `billing`, `billing_webhook` (Stripe決済)<br>- `auth` (JWT/RBAC認証)<br>- `trace`, `health`, `metrics` (監視)<br>- `anti_ai`, `subtext`, `annotations` | 単なる小説生成アプリから、認証・課金決済・OpenTelemetry/Healthメトリクス・サブテキスト解析・アノテーション（Frontmatter等）を備えた商用バックエンドに拡張されています。 |
| **フロントエンド構成** | 「かんたんモード」「上級者Studio」のペイン紹介 | **ウィザード導線・コンポーネントの高度モジュール化**<br>- `WizardWorkflowPage.tsx`<br>- `components/wizard/`, `studio/`, `billing/`, `commercial/`, `illustrations/` 等 | `App.tsx` の肥大化解体計画（`PLAN_P2_ARCHITECTURE_CONSOLIDATION_36STEPS.md`）が進められており、ウィザード形式ページや多数の特化パネルに分割されています。 |
| **納品パッケージ (ZIP)** | `01_本文.txt` 〜 `04_データダンプ.json` の固定4構成 | カクヨム・なろう向けエクスポート、EPUB、プラットフォーム別変換エンジンが追加 | `publishing` ルーターおよび `platform_export` ルーターによるマルチプラットフォーム出力対応が拡充されています。 |
| **将来計画・ロードマップ** | `TEST_COVERAGE_PLAN.md` への参照 | **マスターロードマップ (SSOT) が新設**<br>- `plans/PHASE_ROADMAP_MASTER.md`<br>- Phase 0〜3 の4段階構想 | 過去の無数の計画書（P0〜P10等）は `plans/archive/v4_legacy/` に退避され、止血・コア救命・エージェント軽量化・環境統一の **4段階マスターロードマップ** に一本化されています。 |

---

## 🔍 主な注目点と今後の開発への示唆

1. **ドメイン層への統合（`src/domain/writing`）**:
   - `WritingService` は `src/domain/writing/` が正本（SSOT）です。README のコード例（`AppContainer` からの取得やインポートパス）を `src.domain.writing` ベースに更新すると開発者の混乱が防げます。
2. **統一 CLI `autonovel` の公式化**:
   - READMEのクイックスタートや開発ワークフローに `autonovel check-env` や `autonovel balance` の利用方法を記載することで、個別スクリプト起動の手間が減らせます。
3. **プラグイン機構と決済・認証機能の明記**:
   - README は主に執筆機能にフォーカスしていますが、実際には **Stripe 課金 (`billing`)**、**認証 (`auth`)**、**プラグインレジストリ (`plugins`)** が実装されています。これらを「商用機能 / 拡張アーキテクチャ」として README に追記すると、現在のプロダクトの実態と合致します。
4. **バージョン番号の整合**:
   - `pyproject.toml` (5.0.3) と `src/cli/main.py` (5.1.0) のバージョン表記の不整合を解消することが推奨されます。
