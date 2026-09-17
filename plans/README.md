# AutoNovel 計画書インデックス

本ディレクトリは、AutoNovel の健全化・商用化に向けたアクティブな計画書を管理しています。

## 📌 現在アクティブなマスター計画書

| 計画書 | 概要 | ステータス |
|:---|:---|:---:|
| [V5_RELEASE_ROADMAP.md](./V5_RELEASE_ROADMAP.md) | **v5.0 リリース方針・将来戦略ロードマップ (Next-Gen)**<br>Pillar 1〜4（脱AGE・統合オーディター・30秒生成・EPUB特化） | 🎯 将来方針 |
| [PHASE_ROADMAP_MASTER.md](./PHASE_ROADMAP_MASTER.md) | **健全化・商用化マスターロードマップ (SSOT)**<br>フェーズ0（止血・身軽化）〜フェーズ3（商用ローンチ）の全体計画 | 🚀 実行中 |
| [PLAN_LOW_COST_COMMERCIALIZATION_ROADMAP.md](./PLAN_LOW_COST_COMMERCIALIZATION_ROADMAP.md) | 低コスト商用化ロードマップ（ゼロ予算公開戦略・料金モデル） | 📋 参照 |

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

## 📦 過去の計画書アーカイブ
過去の細分化された計画書（P0〜P10、旧カバレッジ72ステップ、旧プロポーザル等）はすべて以下に保管されています：
- [plans/archive/v4_legacy/](./archive/v4_legacy/)