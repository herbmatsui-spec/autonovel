# OpenAPI 型マッピングマトリクス

このドキュメントは、バックエンドの Pydantic モデル、OpenAPI 仕様書のスキーマ、およびフロントエンドの TypeScript 型の対応関係を定義したものです。

## マッピング表

| バックエンド Pydantic モデル (`api_schemas.py`) | OpenAPI Schema (`openapi.json`) | フロントエンド TS 型 (`api.ts`) | 備考 |
| :--- | :--- | :--- | :--- |
| `BookSchema` | `Book` | `Book` | |
| `PlotSchema` | `Plot` | `Plot` | |
| `ChapterSchema` | `Chapter` | `Chapter` | |
| `BibleSchema` | `Bible` | `Bible` | |
| `OptimizationReportSchema` | `OptimizationReport` | `OptimizationHistory` | 名称に乖離あり。移行時に `OptimizationHistory` としてエイリアス設定 |
| `TaskStatusSchema` | `TaskStatus` | `TaskStatus` | |
| `EasyModeRequest` | `EasyModeRequest` | `EasyModeParams` | Request $\rightarrow$ Params |
| `EpisodeGenerateRequest` | `EpisodeGenerateRequest` | `EpisodeGenerateParams` | Request $\rightarrow$ Params |
| `PlanGenerationRequest` | `PlanGenerationRequest` | `PlanGenerationParams` | Request $\rightarrow$ Params |
| `RetryFailedRequest` | `RetryFailedRequest` | `RetryFailedParams` | Request $\rightarrow$ Params |
| `PlotExpandRequest` | `PlotExpandRequest` | `PlotExpandParams` | Request $\rightarrow$ Params |
| `PlotRebuildRequest` | `PlotRebuildRequest` | `PlotRebuildParams` | Request $\rightarrow$ Params |
| `CritiqueOptimizeRequest` | `CritiqueOptimizeRequest` | `CritiqueOptimizeParams` | Request $\rightarrow$ Params |
| `AuditPlanRequest` | `AuditPlanRequest` | `AuditPlanParams` | Request $\rightarrow$ Params |
| `ChapterImportRequest` | `ChapterImportRequest` | `ChapterImportParams` | Request $\rightarrow$ Params |
| `MarketingGenerateRequest` | `MarketingGenerateRequest` | `MarketingGenerateParams` | Request $\rightarrow$ Params |
| `PendingPatch` (Internal) | `PendingPatch` | `PendingPatch` | |
| `PromptVersion` (Internal) | `PromptVersion` | `PromptVersion` | |
| `NarrativeMetricTrend` (Internal) | `NarrativeMetricTrend` | `NarrativeMetricTrend` | |

## 注意点
- **名称の乖離**: `OptimizationReport` $\rightarrow$ `OptimizationHistory` のように、バックエンドとフロントエンドで名称が異なるものが存在します。移行時はフロントエンドの既存コードを壊さないよう、`api.ts` 内でエイリアスを定義します。
- **Request $\rightarrow$ Params**: フロントエンドではリクエストボディを `Params` と呼称して定義しているため、これらもエイリアスで吸収します。
