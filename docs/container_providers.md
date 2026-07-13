# AppContainer Provider 一覧

## 概要

`src/core/container.py` に定義されている `AppContainer` の全 Provider をリスト化し、依存関係を可視化します。

## Provider リスト

### 1. 外部入力 / 基本設定
| Provider名 | 型 | 説明 | 依存関係 |
|-------------|-----|------|----------|
| `api_key` | `providers.Object` | Gemini APIキー | なし |
| `global_config` | `providers.Singleton` | 全局設定 (`get_config`) | なし |

### 2. インフラストラクチャ層
| Provider名 | 型 | 説明 | 依存関係 |
|-------------|-----|------|----------|
| `db` | `providers.Singleton` | データベースマネージャ (`get_db_manager`) | なし |
| `vector_store` | `providers.Singleton` | ベクターストア (現在 lambda: None) | なし |
| `audit_logger` | `providers.Singleton` | 監査ロガー (現在 lambda: None) | なし |
| `cooldown` | `providers.Singleton` | 適応的冷却時間管理 (`AdaptiveCooldown`) | なし |
| `genai_client` | `providers.Singleton` | Gemini APIクライアント | `api_key` |
| `llm_factory` | `providers.Singleton` | LLMプロバイダファクトリ | `genai_client`, `cooldown` |
| `semantic_cache` | `providers.Singleton` | セマンティックキャッシュ管理 | `vector_store` |
| `llm` | `providers.Singleton` | LLM生成結果プロキシ | `llm_factory` |
| `connection_pipeline` | `providers.Singleton` | 通信パイプライン (現在 lambda: None) | なし |

### 3. データアクセス層
| Provider名 | 型 | 説明 | 依存関係 |
|-------------|-----|------|----------|
| `repo` | `providers.Singleton` | データリポジトリ (`DataRepository`) | `db` |
| `uow` | `providers.Factory` | Unit of Work (`UnitOfWork`) | `db` |

### 4. ビジネスロジック / 共通サービス
| Provider名 | 型 | 説明 | 依存関係 |
|-------------|-----|------|----------|
| `pm` | `providers.Singleton` | プロンプトマネージャ (`PromptManager`) | なし |
| `ctx_mgr` | `providers.Singleton` | コンテキストマネージャ (`ContextManager`) | `repo` |

### 5. エージェント / 専門サービス
| Provider名 | 型 | 説明 | 依存関係 |
|-------------|-----|------|----------|
| `auditor` | `providers.Singleton` | 論理監査エージェント (`LogicalAuditor`) | `repo`, `pm`, `llm`, `ctx_mgr` |
| `marketing` | `providers.Singleton` | マーケティングエージェント (`MarketingAgent`) | `repo`, `pm`, `llm` |
| `bible_generator` | `providers.Singleton` | バイブル生成エージェント (`WorldBibleGenerator`) | `repo`, `llm`, `pm`, `marketing`, `auditor` |
| `plot_expander` | `providers.Singleton` | プロット展開エージェント (`PlotExpander`) | `repo`, `llm`, `pm`, `auditor` |
| `planner` | `providers.Singleton` | 計画エージェント (`PlanningAgent`) | `repo`, `pm`, `ctx_mgr`, `auditor`, `bible_generator`, `plot_expander` |
| `validator` | `providers.Singleton` | 論理監査バリデータ (`LogicalAuditor`) | `repo`, `pm`, `llm`, `ctx_mgr` |
| `narrative` | `providers.Singleton` | ナラティブコントローラ (`NarrativeController`) | `llm`, `repo`, `pm`, `ctx_mgr`, `validator`, `auditor` |
| `critique` | `providers.Singleton` | 批評エージェント (`CritiqueAgent`) | `repo`, `pm`, `llm` |
| `style_rag` | `providers.Singleton` | スタイルRAGマネージャ (`StyleRagManager`) | `genai_client`, `repo` |
| `writer` | `providers.Singleton` | 執筆エージェント (`WritingAgent`) | `repo`, `llm`, `pm`, `ctx_mgr`, `narrative`, `critique`, `plot_expander`, `style_rag`, `uow`, `global_config`, `planner` |
| `formatter` | `providers.Singleton` | カクヨムフォーマッタ (`KakuyomuFormatter`) | なし |

## 依存関係の特記事項

- **最上位依存**: `Writer` がほぼ全ての主要エージェントと設定に依存しており、システムの最終的な統合点となっています。
- **コア依存チェーン**: `db` $\rightarrow$ `repo` $\rightarrow$ `ctx_mgr`/`auditor` $\rightarrow$ `planner` $\rightarrow$ `writer`
- **LLMチェーン**: `api_key` $\rightarrow$ `genai_client` $\rightarrow$ `llm_factory` $\rightarrow$ `llm` $\rightarrow$ `Agents`
