# エンジンメソッド一覧 (UltimateHegemonyEngine)

| メソッド名 | 責務 | 委譲先候補 |
|------------|------|------------|
| `sync_bible` | Bibleのライフサイクル同期 | `BibleService` |
| `resolve_bible_setting` | 仮設定のステータス更新 | `BibleService` |
| `generate_plot` | プロット生成 | `PlotService` |
| `write_episode` | エピソード執筆 | `WritingService` |
| `audit_narrative` | 物語の整合性監査 | `AuditService` |
| `optimize_critique` | 批評の最適化 | `CritiqueService` |
| `marketing_gen` | マーケティング生成 | `MarketingService` |
| `plan_rebuild` | プロット再構築 | `PlanningService` |
| `style_rag_query` | スタイルRAGクエリ | `StyleRagService` |
