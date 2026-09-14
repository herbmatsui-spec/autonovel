# AutoNovel 改善提案・実装計画書インデックス

AutoNovel の品質向上・商用化に向けたアクティブな実装計画書一覧です。
すべての計画書は「全12ステップ・完全自己完結コード付属」で設計されています。

## 📋 アクティブ計画書一覧

| 計画書 | 提案名 | 状態 | 目的 |
|:---|:---|:---:|:---|
| [PROPOSAL_01_ARCHITECTURE_UNIFICATION_PLAN.md](./PROPOSAL_01_ARCHITECTURE_UNIFICATION_PLAN.md) | 新旧アーキテクチャ一本化 & デッドコード物理パージ | ✅ 完了 | 死蔵コード削除、リポジトリ層集約、BookMapper |
| [PROPOSAL_02_AUTH_GUARD_AND_IDOR_12STEPS.md](./PROPOSAL_02_AUTH_GUARD_AND_IDOR_12STEPS.md) | 全ルーター認可ガード & IDOR防止 | ⏳ 準備完了 | 38ルーター認可網羅、所有権ガード、RBAC |
| [PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md](./PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md) | OpenAPI駆動 End-to-End 型同期 | ⏳ 準備完了 | スキーマ抽出、TypeScript型生成、RFC 7807 |
| [PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md](./PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md) | LLMサーキットブレーカー & トークン予算ガード | ⏳ 準備完了 | API障害フェイルオーバー、PDCA上限強制停止 |
| [PROPOSAL_09_CLEANUP_AND_CONFIG_SSOT_12STEPS.md](./PROPOSAL_09_CLEANUP_AND_CONFIG_SSOT_12STEPS.md) | 計画書インフレ解消 & 設定情報源SSOT一元化 | ⏳ 本書 | ドキュメント退避、config.py一元化、.env整合 |

## 📦 過去ドキュメント
過去の完了済み計画書や検討メモは `docs/archive/plans_v4/` に保管されています。