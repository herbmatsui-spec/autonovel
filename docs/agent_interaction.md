# エージェント相互作用図

```mermaid
graph LR
    PlanningAgent[PlanningAgent] -->|アーク生成| PlotRebuildWorkflow[PlotRebuildWorkflow]
    PlanningAgent -->|プロット案| PlotAgent[PlotAgent]
    PlotRebuildWorkflow -->|プロット展開指示| PlotAgent[PlotAgent]
    PlotAgent -->|プロット| WritingAgent[WritingAgent]
    WritingAgent -->|執筆内容| CritiqueAgent[CritiqueAgent]
    CritiqueAgent -->|修正指示| WritingAgent
    WritingAgent -->|完成原稿| MarketingAgent[MarketingAgent]
    MarketingAgent -->|宣伝文| User[ユーザー]
```

## 再構築パイプライン (Proposal C)

プロット再構築は `PlotRebuildWorkflow` がオーケストレーターとして担当する。
`PlanningAgent` はアーク生成 (`generate_arcs`) のみ、`PlotAgent` はプロット展開
(`expand_plots`) のみを担い、再構築ロジックの重複を排除している。
