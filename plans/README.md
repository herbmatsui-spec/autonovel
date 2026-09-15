# AutoNovel 改善提案・実装計画書インデックス

AutoNovel の品質向上・商用化に向けたアクティブな実装計画書一覧です。
すべての計画書は**「全12ステップ・完全自己完結コード（コピペで動作可能）・単体テスト・検証コマンド付属」**で設計されています。

## 📋 アクティブ計画書一覧

| 計画書 | 提案名 | 状態 | 目的・主要対象 |
|:---|:---|:---:|:---|
| [PROPOSAL_01_ARCHITECTURE_UNIFICATION_PLAN.md](./PROPOSAL_01_ARCHITECTURE_UNIFICATION_PLAN.md) | 新旧アーキテクチャ一本化 & デッドコード物理パージ | ✅ 実装済 | 死蔵コード削除（2,688行削減）、リポジトリ層集約、BookMapper |
| [PROPOSAL_02_AUTH_GUARD_AND_IDOR_12STEPS.md](./PROPOSAL_02_AUTH_GUARD_AND_IDOR_12STEPS.md) | 全ルーター認可ガード & IDOR防止 | ✅ 実装済 | 認可ガード網羅、所有権ガード（IDOR防止）、RBAC（Admin/Pro/Free） |
| [PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md](./PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md) | OpenAPI駆動 End-to-End 型同期 | ✅ 実装済 | スキーマ抽出、TypeScript型生成、RFC 7807 ProblemDetails |
| [PROPOSAL_04_CHECKPOINTED_RESUME_12STEPS.md](./PROPOSAL_04_CHECKPOINTED_RESUME_12STEPS.md) | 長時間執筆タスクの中断・再開機構 | ⏳ 準備完了 | ワークフロー各ステップ状態永続化、DLQ、中断タスクのResume API |
| [PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md](./PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md) | LLMサーキットブレーカー & トークン予算ガード | ✅ 実装済 | API障害フェイルオーバー、PDCA上限強制停止、課金事故防止 |
| [PROPOSAL_06_DB_DIALECT_AND_MIGRATIONS_12STEPS.md](./PROPOSAL_06_DB_DIALECT_AND_MIGRATIONS_12STEPS.md) | DB方言差（SQLite/Postgres）吸収 & マイグレーション堅牢化 | ⏳ 準備完了 | TypeDecorator（JSON/Vector/DateTime）、往復検証スクリプト |
| [PROPOSAL_07_EDITOR_AUTOSAVE_AND_CRASH_RECOVERY_12STEPS.md](./PROPOSAL_07_EDITOR_AUTOSAVE_AND_CRASH_RECOVERY_12STEPS.md) | エディタのローカルファースト自動保存 & クラッシュ復旧 | ⏳ 準備完了 | IndexedDB非同期キャッシュ（500ms）、復元モーダル、Online/Offline |
| [PROPOSAL_08_DOCKER_OPTIMIZATION_AND_HEALTHCHECK_12STEPS.md](./PROPOSAL_08_DOCKER_OPTIMIZATION_AND_HEALTHCHECK_12STEPS.md) | Dockerマルチステージ最適化 & ヘルスチェック分離 | ⏳ 準備完了 | イメージ軽量化、非特権ユーザー、/health/liveness & /health/readiness |
| [PROPOSAL_09_CLEANUP_AND_CONFIG_SSOT_12STEPS.md](./PROPOSAL_09_CLEANUP_AND_CONFIG_SSOT_12STEPS.md) | 計画書インフレ解消 & 設定情報源SSOT一元化 | ✅ 実装済 | 計画書アーカイブ、config.py一元化、.env.example 65キー完全同期 |

## 🧪 テストカバレッジ80%突破 実装計画書一覧（全72ステップ）

| 計画書 | レイヤー | 状態 | 目的・主要対象 |
|:---|:---|:---:|:---|
| [P0_COVERAGE_MASTER_ROADMAP_72STEPS.md](./P0_COVERAGE_MASTER_ROADMAP_72STEPS.md) | 全リポジトリ統合 | 🚀 アクティブ | 21.86%→80.0%突破の全体設計、定量試算、低性能LLMプロンプト |
| [P1_COVERAGE_DATABASE_12STEPS.md](./P1_COVERAGE_DATABASE_12STEPS.md) | データベース・インフラ層 | 🚀 アクティブ | `src/backend/database/`, `src/infrastructure/` (+2,600行) |
| [P2_COVERAGE_SERVICES_12STEPS.md](./P2_COVERAGE_SERVICES_12STEPS.md) | サービス・キャッシュ・検索層 | 🚀 アクティブ | `src/services/` (Redis, Vector, RAG, BookScore) (+4,800行) |
| [P3_COVERAGE_AGENTS_12STEPS.md](./P3_COVERAGE_AGENTS_12STEPS.md) | エージェント・執筆＆監査層 | 🚀 アクティブ | `src/agents/` (Writing, 8 Specialists, Erotic) (+4,500行) |
| [P4_COVERAGE_WORKFLOWS_12STEPS.md](./P4_COVERAGE_WORKFLOWS_12STEPS.md) | ワークフロー・タスク実行層 | 🚀 アクティブ | `src/backend/workflows/`, `tasks/`, `background.py` (+3,600行) |
| [P5_COVERAGE_EASYMODE_12STEPS.md](./P5_COVERAGE_EASYMODE_12STEPS.md) | Easy Mode・出版エクスポート層 | 🚀 アクティブ | `src/easy_mode/`, `publishers/`, `multimedia` (+3,300行) |
| [P6_COVERAGE_ROUTERS_DOMAIN_12STEPS.md](./P6_COVERAGE_ROUTERS_DOMAIN_12STEPS.md) | APIルーター・ドメイン・コア層 | 🚀 アクティブ | `routers/`, `domain/`, `core/`, `sanitizer.py`, `auth.py` (+5,500行) |

## 📦 過去ドキュメント
過去の完了済み計画書や検討メモは `docs/archive/plans_v4/` に保管されています。