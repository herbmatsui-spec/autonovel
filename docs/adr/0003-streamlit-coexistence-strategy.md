# ADR-0003: Streamlit共存・廃止方針

**Date:** 2026-07-11
**Status:** Accepted
**Decider(s):** 開発チーム

### 1. Context and Problem Statement

現在、本プロジェクトには2つのUI層が存在する：
- **Streamlit (backend/)**: 既存のGUI。足が速い開発が可能だが、商用レベルのUI/UXには不向き。
- **React (frontend/src/)**: 足場（package.json, tsconfig, tailwind）は整備済みだが、実装は空。

この状態が続くと、「第三者がReactを稼働前提と誤認して触れる事故リスク」「二重開発コスト」「技術的負債の蓄積」が発生する。

### 2. Decision to be Made

React実装が完了するまでの間、Streamlitをどのように扱うか。また、React реализация本格開始後のStreamlitの扱い方針。

### 3. Considered Options

- **Option 1: 即時廃止**
  - Pros: コードベースが一つになり、管理コストが削減される。
  - Cons: React実装が未完了のため、開発速度が大幅に低下する。

- **Option 2: 無期限併存**
  - Pros: 開発速度を維持できる。必要に応じて両oyerを使い分け可能。
  - Cons: 二重メンテナンスコスト。UI不整合のリスク。

- **Option 3: 段階的移行（本採用）**
  - Reactが特定機能（プロット編集、キャラクター管理など）を реализация完了したら、Streamlitの奥の機能を段階的に無効化。
  - 最終目標：Reactへの完全移行。

### 4. Decision Outcome

**Chosen Option: Option 3（段階的移行）**

**Justification:**
- 即時廃止は開発速度を殺ぐため不可。
- 無制限併存は技術的負債を増やす。
- 段階的移行なら、開発速度を維持しつつ、UI/UX向上とコード整理を並行して進められる。

### 5. Consequences

- **Positive:**
  - 開発速度維持（Streamlitで 긴급対応OK）
  - UI/UX向上への明確な道筋
  - 責任の所在が明確化（実装済み機能はReact、未実装はStreamlit）

- **Negative/Trade-offs:**
  - 一時的に2つのコードベースを管理するコスト
  - 切り替えタイミングの判断が必要

- **Risks:**
  - Streamlit кодが放置され、陈腐化风险
  - 切り替え时期的混乱

### 6. Implementation Notes

| フェーズ | React実装機能 | Streamlit状態 |
|----------|---------------|---------------|
| Phase 0  | （なし）       | メインヘルス維持 |
| Phase 1  | ダッシュボード、共通Layout | 既存機能のまま |
| Phase 2  | プロット編集、章管理       | 閲覧のみ可能 |
| Phase 3  | キャラクター管理           | 閲覧のみ可能 |
| Phase 4  | 生成・編集すべての機能     | 完全廃止・削除 |

### 7. Notes/References

- [ADR-0001: アーキテクチャリファクタリング方針](../adr/0001-architecture-refactoring-policy.md)
- [ADR-0002: AIオーケストレーションフレームワーク](../adr/0002-ai-orchestration-framework.md)
- 関連ISSUE: GitHub Issuesの「frontend実装」ラベル参照