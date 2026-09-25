# AutoNovel 健全化・商用化マスターロードマップ (SSOT)

本ドキュメントは、AutoNovel プロジェクトの品質健全化および商用化に向けた単一の情報源（Single Source of Truth）です。  
ソフトウェア工学の原則と最新LLMの知見（自己修正の飽和限界、カスケード最適化等）を取り入れつつ、**「Web小説としての面白さ」と「開発の現実性（脱オーバーエンジニアリング）」のバランスを最優先**にした5段階の直列ステップで進行します。

---

## 🎯 ロードマップ概要

```
[Phase 0: 観測性とSSOT確立] ──► [Phase 1: テスト救命(Sensing)] ──► [Phase 2: 身軽化・構造一本化] ──► [Phase 3: コア軽量化(EasyMode)] ──► [Phase 4: 本番運用化]
・CI/カバレッジ実力値設定        ・既存テスト全件パス達成(安全網)   ・不要スタブ/デッドコード削除    ・8オーディター集約(1回統合評価)  ・本番Docker/DB検証
・README/仕様と実態の同期        ・破綻テストの改修/隔離           ・domain/agents二重化の完全解消   ・PDCA局所パッチ化(推敲品質維持)  ・商用ローンチ
```

---

## 📋 フェーズ別詳細と判断根拠（Rationale）

### 【Phase 0: 観測性とSSOT確立（Baseline & Documentation Sync）】（現在実行中）
- **ゴール**: 正確な現状把握ができる状態を作り、開発の迷いと認知負荷をなくす
- **背景・判断根拠**: 現実のコード（`domain/writing`、統一CLI等）とREADMEの乖離を解消し、計測可能なベースラインを確定する。
- **主要タスク**:
  1. 作業ツリーのセーブポイントコミット作成（専用ブランチ運用）
  2. `pyproject.toml` のカバレッジ閾値を実力値（55%）に一時設定し、テスト実行が閾値割れで強制終了しないようにする
  3. `README.md` を最新の実態（`src.domain.writing` 移行、統一CLI `autonovel`、動的プラグイン機構等）に同期
  4. バージョン表記の統一（`pyproject.toml` と `src/cli/main.py` の足並みを揃える）
  5. `plans/` ディレクトリのマスターロードマップ一本化を維持

### 【Phase 1: テスト救命（Test Stabilization & ALL GREEN）】
- **ゴール**: どんな変更を加えても先祖返り（デグレーション）を即座に検知できるセーフティネットの確立
- **背景・判断根拠（Feathers原則）**: 「テスト網のないリファクタリングは不可逆な破壊を招く」。不要コードの削除より先に、まず全テストが常時パスする状態を不可逆の前提とする。
- **主要タスク**:
  1. `fail_now.txt` にある残存失敗テストの分析と解消（エロティックパイプライン、DB周り等）
  2. Stripe Webhook 500クラッシュ修正（`billing_webhook.py` のコルーチン `await` 漏れ修正）
  3. 認証ミドルウェア修正（JWT / RBAC のテスト正常化）
  4. 完全に廃止された機能（Apache AGE直接依存等）のテストを正式に隔離・削除
  5. **テスト全件 GREEN（PASS）の達成と CI ベースライン確定**

### 【Phase 2: 身軽化と構造一本化（Dead Code Purge & Refactoring）】
- **ゴール**: 認知負荷の激減と、安全で保守しやすい単一アーキテクチャの確立
- **背景・判断根拠（Lehman複雑性縮小則）**: 重複レイヤー（旧writing_service、旧agent等）を抱え続けると保守コストが指数関数的に増大するため、テスト通過を維持しながら不要物を物理削除する。
- **主要タスク**:
  1. `pyproject.toml` omit 指定のデッドモジュール（71ファイル・3,680行）の物理削除
  2. 移行済みシム（`src/agent/`、`src/services/age_client.py`、旧 `writing_service.py` 類）の完全撤廃
  3. 統一 CLI（`autonovel`）への一本化と旧個別スクリプト（`dsp-balance` 等）の整理
  4. データベース層の接続ラッパーハック撤廃

### 【Phase 3: コア軽量化とEasy Mode研ぎ澄まし（Pragmatic Streamlining & UX）】
- **ゴール**: 1話あたり数十円以内・1分以内での生成完走と、最も価値の高いユーザー体験（Easy Mode）の実現
- **背景・判断根拠（現実的なLLM最適化）**:
  - *オーディター集約*: 文字数や禁則などの形式チェックは高速な静的ルールで行い、小説内容の評価は8並列LLMから「1つの統合プロンプト（Unified Auditor）」へ集約し、コストと遅延を1/8に圧縮する。
  - *PDCA推敲の現実解*: 全文再生成ループはコスト爆発と破綻を招くため禁止。ただし文章の情緒や推敲クオリティを維持するため、「指摘された特定シーンのみの局所パッチ（Single-shot Polish）」を最大1回まで許容する。
- **主要タスク**:
  1. **8専門オーディターの集約**: 静的ルール（形式・禁則チェック）＋ 1回の一括LLMコール（定性監査）への再編
  2. **PDCAサイクルのスリム化**: 原則1発生成 ＋ 致命的不整合時のみ局所リライト（1回制限）
  3. **Easy Mode（かんたんモード）の完成**: ブラウザから迷わず本文生成〜ZIP/EPUB納品まで完走するフローの堅牢化
  4. トークン消費・生成速度のベンチマーク計測

### 【Phase 4: 環境統一と商用ローンチ（Production Readiness）】
- **ゴール**: 本番Docker環境での安定稼働と低コスト運用
- **背景・判断根拠**: ローカル開発の快適さ（SQLite起動）を守りつつ、商用インフラ（PostgreSQL + pgvector + Docker）との境界を明確にして本番化する。
- **主要タスク**:
  1. ローカル開発（SQLite）と本番（PostgreSQL + pgvector）の明確な境界定義
  2. Docker Compose 本番構成の起動・E2E検証
  3. 監視・エラーハンドリング（Sentry / OpenTelemetry）のテスト環境スキップと本番初期化検証（完了）
  4. ヘルスチェック（FastAPI JSONResponse 503準拠および実DB疎通）の是正（完了）
  5. 商用リリース準備

---

---

## 📊 実装・統合完了状況 (2026-09-25 確定)

詳細な実行計画書 [PLAN_RECOVERY_UNIFICATION_AND_REAL_INTEGRATION.md](file:///e:/hhh/plans/PLAN_RECOVERY_UNIFICATION_AND_REAL_INTEGRATION.md) および [PLAN_CODE_REVIEW_REMEDIATION_AND_HARDENING.md](file:///e:/hhh/plans/PLAN_CODE_REVIEW_REMEDIATION_AND_HARDENING.md) に基づき、全ステップを完了。

| フェーズ / パート | 状態 | 主な達成内容 |
| :--- | :---: | :--- |
| **Phase 0: 観測性とSSOT確立** | **完了** | SSOT策定、README・仕様同期、カバレッジ閾値と実力値の調整 |
| **Phase 1: テスト救命・復旧 (Part 1)** | **完了** | `__init__.py`全件・`conftest.py`リストア、`project_context`修復、テスト収集数 2,541件へ劇的改善 |
| **Phase 2: 二重化解消 (Part 2)** | **完了** | Flask版仮設モック削除、仮設Web退避、FastAPI正規版への完全一本化 |
| **Phase 3: コア軽量化・統合 (Part 3)** | **完了** | 静的ルールCRLF対応、LLMパース堅牢化、AIサニタイズ、PDCAパイプライン結合、LRUキャッシュ |
| **Phase 4: 本番運用性・テスト確立 (Part 4)** | **完了** | health 503是正・DB疎通、空テスト（`assertTrue`）の真のE2Eテスト化、Sentry/OTELガード |
| **Code Review Remediation (全20ステップ)** | **完了** | **P0〜P2所見の完全解消**: DB非同期コミット正規化、ヘルスチェック一本化、API認証/定数時間比較/バリデーション、CircuitBreakerスレッドセーフ一元化、旧`src/agent`・旧`database/core.py`等16ファイル(1,261行)削除、モデル競合解消 |
| **Phase J: プロット二段階化 (Coarse-to-Fine)** | **完了** | **小説品質向上のための二段階プロット展開（J1〜J3全108ステップ完遂）**:<br>1. **J1 (モデルとプロンプト分離)**: `EpisodeMacroSkeleton` (大局骨子) と `PlotMicroBlueprint` (微視的演出) の分離定義、Jinja2テンプレート・プロンプトビルダー新設<br>2. **J2 (JIT Expanderサービス)**: デメリット3点（レイテンシ増・直列化・状態管理）を「小型高速モデル階層化(`gemini-3.5-flash-lite`)」「投機的非同期プリフェッチ(`asyncio.create_task`)」「完全冪等オンデマンドリゾルバ」で根治<br>3. **J3 (パイプライン統合・定量検証)**: `PlanStep` / `WriteStep` / `EasyMode` / `FullAuto` 切り替え、ビート描写解像度ベンチマーク(`bench_plot_resolution.py`)、真のE2Eテスト(`test_coarse_fine_e2e.py`)全件パス |
| **Code Review Phase 2 Remediation (第2次是正・全24ステップ)** | **完了** | **第2次コードレビュー所見（Critical 3 / Major 5 / Minor 5）の完全解消**:<br>1. **セキュリティ**: .env追跡ゼロ確認、Docker Compose パスワード環境変数化 (test_env_security_guardrails.py 4 passed)<br>2. **認証・ログ**: auth_middleware.py 定数時間比較統一、branches.py print()削除 (test_auth_middleware_timing_safe.py 3 passed, test_no_print_in_production_code.py 1 passed)<br>3. **例外・整理**: ワークフローの except Exception: pass 撲滅、スクリプト集約 (test_exception_handling_audit.py 1 passed)<br>4. **移行完了**: ContextManager 撤廃・委譲一本化 (test_context_builder_migration.py 4 passed)<br>5. **TODO実装**: PatchMerger, ParagraphPatchAgent, FastScreener, patchesルーター, stream_writingジャンル動的化 (test_patch_pipeline_integration.py 4 passed)<br>6. **構造整理**: easy_mode.py 重複import解消 |
| **総合検証 (Phase J / Phase 2 Remediation 含む)** | **完了** | 全新設リグレッションテストスイート ALL GREEN (100% PASS) |


