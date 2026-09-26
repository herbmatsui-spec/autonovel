# AutoNovel 計画書インデックス

本ディレクトリは、AutoNovel の健全化・商用化に向けたアクティブな計画書を管理しています。

## 📌 現在アクティブなマスター計画書

| 計画書 | 概要 | ステータス |
|:---|:---|:---:|
| [V5_RELEASE_ROADMAP.md](./V5_RELEASE_ROADMAP.md) | **v5.0 リリース方針・将来戦略ロードマップ (Next-Gen)**<br>Pillar 1〜4（脱AGE・統合オーディター・30秒生成・EPUB特化） | 🎯 将来方針 |
| [PHASE_ROADMAP_MASTER.md](./PHASE_ROADMAP_MASTER.md) | **健全化・商用化マスターロードマップ (SSOT)**<br>フェーズ0（止血・身軽化）〜フェーズ3（商用ローンチ）の全体計画 | 🚀 実行中 |
| [PLAN_LOW_COST_COMMERCIALIZATION_ROADMAP.md](./PLAN_LOW_COST_COMMERCIALIZATION_ROADMAP.md) | 低コスト商用化ロードマップ（ゼロ予算公開戦略・料金モデル） | 📋 参照 |
| [PLAN_I1_UNIFIED_ILLUSTRATION_ENGINE_24STEPS.md](./PLAN_I1_UNIFIED_ILLUSTRATION_ENGINE_24STEPS.md) | **統合イラスト生成エンジン**<br>3系統（Traditional/IllustrationPoint/Manga24）統合、生成モデルは NanoBanana2Lite に全種別統一、モデル差し替えは設定1行 | ✅ 実装完了 |

---

## 🛠️ v5.0 詳細実装計画書（各24極小ステップ・計96ステップ）

低性能なLLMや自律エージェントでも確実に1ステップずつ適用・検証可能なように、全ステップに「対象ファイル」「自己完結コード」「検証コマンド」「期待結果」を完備しています。

| 計画書 | 対象ピラー | 主要テーマ | ステップ数 |
|:---|:---|:---|:---:|
| [V5_A1_STREAMLINED_AGENT_24STEPS.md](./V5_A1_STREAMLINED_AGENT_24STEPS.md) | **Pillar 1** | **Streamlined Agent Flow**<br>8専門オーディター統合、二層監査（静的0ms＋定性単一LLM）、1パッチPDCA | 全24ステップ |
| [V5_A2_RELATIONAL_MEMORY_24STEPS.md](./V5_A2_RELATIONAL_MEMORY_24STEPS.md) | **Pillar 2** | **Relational Simplicity & Foreshadowing**<br>脱Apache AGE（グラフDB撤廃）、伏線ステートマシン、3層ローリング記憶 | 全24ステップ |
| [V5_A3_ZERO_COST_INFRA_24STEPS.md](./V5_A3_ZERO_COST_INFRA_24STEPS.md) | **Pillar 3** | **Zero-Cost Infra & Pure Creative Pipeline**<br>自前GPU排除（オンデマンドAPI移行）、整形コピー特化、商用縦書きEPUB 3、コストガード | 全24ステップ |
| [V5_A4_UNIFIED_DOMAIN_TYPESYNC_24STEPS.md](./V5_A4_UNIFIED_DOMAIN_TYPESYNC_24STEPS.md) | **Pillar 4** | **Unified Domain Model & Type-Safe UX**<br>Pydantic v2統一ドメインモデル、OpenAPI型同期（TypeSync/8GB問題解消）、3ステップ共創UI、SSEストリーミング | 全24ステップ |

---

## 🚨 v5.0 完成形メタ計画書（コードレビュー指摘対応 / 全108ステップ）

`ec728cdc` のコードレビューで確定した実行時バグ・データ整合性・API 衛生の問題に対する実装計画です。
**C1 → C2 → C3 の順に実施**してください（各計画書は前計画の完了を前提としています）。
イラスト生成系は本計画の対象外です（別計画で扱う）。

| 計画書 | 対象 | 主要テーマ | ステップ数 | ステータス |
|:---|:---:|---|:---:|:---:|
| [PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md](./PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md) | **P0-1 / P0-2 / P0-7** | 執筆SSE・マーケティング生成のクラッシュ停止、テストスイート緑化（spacy収集エラー・`src.agent` エイリアス撤去・回帰防止テスト8本） | 全36ステップ | ✅ 実装完了 |
| [PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md](./PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md) | **P0-3 / P0-6** | 伏線メモ専用カラム追加（`Plot.foreshadowing_notes`＋マイグレーション0031）、偽伏線の生成停止、冪等化、DIコンテナ（`wiring_config` / `vector_store`）修復 | 全36ステップ | ✅ 実装完了 |
| [PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md](./PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md) | **P0-4 / P1** | `/commercial/planning` を `COMMERCIAL_40EP_BEATS` + `EpisodeBeat` + `PlanningAgent` へ接続、タスク発行化・所有者検証、決済URLの open redirect 対策、遅延プロパティ整理 | 全36ステップ | ✅ 実装完了 |
| [PLAN_C4_PIPELINE_GREEN_AND_COMMIT_PREPARATION_12STEPS.md](./PLAN_C4_PIPELINE_GREEN_AND_COMMIT_PREPARATION_12STEPS.md) | **Pipeline / DoD** | `fakeredis` dev 依存導入・スキップガード追加によるパイプライン全緑化、DoD 同期、コミット準備 | 全12ステップ | ✅ 実装完了 |

---

## 📦 過去の計画書アーカイブ
過去の細分化された計画書（P0〜P10、旧カバレッジ72ステップ、旧プロポーザル等）はすべて以下に保管されています：
- [plans/archive/v4_legacy/](./archive/v4_legacy/)