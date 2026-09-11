# 第3段階: 堅牢性・自律運用フェーズ 72ステップ詳細実装計画書
## （LLM自動フェイルオーバー・NetworkXグラフ完全等価化・オーディター動的ルーティング・障害自己復旧）

- **策定日**: 2026年9月10日
- **対象バージョン**: AutoNovel v4.5.0+
- **設計方針**: 低性能なLLMでも迷わず1ステップずつ確実に実装・検証できるよう、最小単位の作業に分割。12ステップごとに動作検証ゲート（Checkpoint）を設置。
- **総ステップ数**: 全72ステップ（6パート × 12ステップ）

---

## 📋 パート別構成概要

| パート | ステップ | テーマ | 主な対象ファイル | ステータス |
|---|---|---|---|---|
| **Part 1** | Step 1〜12 | LLMマルチプロバイダ自動フェイルオーバー & サーキットブレーカー | `src/llm/resilient_gateway.py`<br>`src/llm/circuit_breaker.py`<br>`src/services/resilience.py` | ⏳ 未着手 |
| **Part 2** | Step 13〜24 | トークン予算・APIコスト監視ガード & 自動モデルダウングレード | `src/services/cost_budget_guard.py`<br>`src/services/token_tracker.py`<br>`src/backend/routers/cost.py` | ⏳ 未着手 |
| **Part 3** | Step 25〜36 | SQLite/スタンドアロン環境向け NetworkX グラフ探索の完全等価化 | `src/services/graph/networkx_store.py`<br>`src/services/graph/hybrid_graph_facade.py`<br>`src/services/age_client.py` | ⏳ 未着手 |
| **Part 4** | Step 37〜48 | 8専門オーディターのLLM動的インテリジェント・ルーティング | `src/agents/specialists/model_router.py`<br>`src/agents/specialist_auditor_base.py`<br>`config/audit_models.yaml` | ⏳ 未着手 |
| **Part 5** | Step 49〜60 | 障害自己修復 & ワーカークラッシュ時の自動リジューム (WAL/Checkpoints) | `src/backend/tasks/worker_recovery.py`<br>`src/backend/tasks/dag_persistence.py`<br>`src/backend/tasks/dag_scheduler.py` | ⏳ 未着手 |
| **Part 6** | Step 61〜72 | カオスエンジニアリング検証 & 第3段階 E2E 包括的回帰テスト | `tests/integration/test_phase3_chaos_resilience.py`<br>`tests/integration/test_phase3_full_regression.py` | ⏳ 未着手 |

---

## 🛡️ Part 1: LLMマルチプロバイダ自動フェイルオーバー & サーキットブレーカー (Step 1〜12)

### Step 1: プロバイダ状態モデル `ProviderHealthState` の定義
- **目的**: 各LLMプロバイダ（OpenAI, Gemini, Claude, OpenRouter, Ollama）の健全性、連続エラー回数、サーキットオープン時刻を管理するデータ構造を定義する。
- **対象ファイル**: `src/llm/circuit_breaker.py` (新規作成)
- **変更内容**:
  ```python
  from dataclasses import dataclass
  from datetime import datetime
  from enum import Enum

  class CircuitState(Enum):
      CLOSED = "closed"      # 正常稼働
      OPEN = "open"          # 遮断中（リクエスト即座遮断・迂回）
      HALF_OPEN = "half_open"# 試験的疎通中

  @dataclass
  class ProviderHealthState:
      provider_name: str
      state: CircuitState = CircuitState.CLOSED
      failure_count: int = 0
      last_failure_time: datetime | None = None
      opened_at: datetime | None = None
      success_count: int = 0
  ```
- **確認コマンド**: `python -c "from src.llm.circuit_breaker import ProviderHealthState; print('OK')"`
- **完了条件**: クラスが定義されインポートできること。

### Step 2: サーキットブレーカー本体 `LLMCircuitBreaker` の実装
- **目的**: 連続N回（デフォルト3回）のタイムアウトまたは5xxエラーでサーキットをOPENにし、Cool-down期間（デフォルト60秒）経過後にHALF-OPENに移行する判定エンジン。
- **対象ファイル**: `src/llm/circuit_breaker.py`
- **変更内容**: `record_success(provider)`, `record_failure(provider, error)`, `can_execute(provider) -> bool` メソッドを実装。
- **確認コマンド**: `python -m py_compile src/llm/circuit_breaker.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 3: フォールバック優先順位チェーン（Fallback Chain）の定義
- **目的**: 主プロバイダ障害時の迂回優先順位（例: Claude ➔ OpenAI (GPT-4o) ➔ Gemini ➔ ローカルOllama/vLLM ➔ Mock）を定義する。
- **対象ファイル**: `src/llm/fallback_policy.py` (新規作成)
- **変更内容**:
  ```python
  DEFAULT_FALLBACK_CHAINS = {
      "claude": ["openai", "gemini", "mock"],
      "openai": ["gemini", "claude", "mock"],
      "gemini": ["openai", "claude", "mock"],
      "ollama": ["mock"],
  }
  ```
- **確認コマンド**: `python -c "from src.llm.fallback_policy import DEFAULT_FALLBACK_CHAINS; print('OK')"`
- **完了条件**: 定義が読み込めること。

### Step 4: 自律回復型ゲートウェイ `ResilientLLMGateway` の設計
- **目的**: アプリケーション全体のLLM呼び出しを一手に引き受け、障害検知時に自動で代替プロバイダへシームレスに切り替えるゲートウェイ。
- **対象ファイル**: `src/llm/resilient_gateway.py` (新規作成)
- **変更内容**: `generate_text(prompt, primary_provider, **kwargs)` メソッド内で、サーキットブレーカーとフォールバックチェーンを適用。
- **確認コマンド**: `python -m py_compile src/llm/resilient_gateway.py`
- **完了条件**: ゲートウェイがコンパイルできること。

### Step 5: レート制限（HTTP 429 Too Many Requests）の特別ハンドリング
- **目的**: レート制限エラー（RateLimitError）が発生した場合、指数バックオフを行うと同時に、即座に次のプロバイダへフォールバックしてタスクを停止させない。
- **対象ファイル**: `src/llm/resilient_gateway.py`
- **変更内容**: `isinstance(err, RateLimitError)` を検知した際の高速フォールバック分岐の追加。
- **確認コマンド**: `python -m py_compile src/llm/resilient_gateway.py`
- **完了条件**: レート制限ハンドラが実装されていること。

### Step 6: 構造化出力（JSON / Pydantic）のフォールバック互換性保証
- **目的**: プロバイダ切り替え時にも、OpenAIのStructured OutputsやGeminiのJSON Modeが壊れないよう、スキーマ指示を共通プロンプト形式へ自動正規化。
- **対象ファイル**: `src/llm/resilient_gateway.py`
- **変更内容**: `normalize_schema_prompt(prompt, response_schema)` ヘルパーの導入。
- **確認コマンド**: `python -m py_compile src/llm/resilient_gateway.py`
- **完了条件**: 正規化ロジックが実装されていること。

### Step 7: Prometheus メトリクスへのフェイルオーバー回数記録
- **目的**: `llm_failover_total{from_provider="...", to_provider="...", reason="..."}` カウンタをインクリメント。
- **対象ファイル**: `src/llm/resilient_gateway.py`
- **確認コマンド**: `python -m py_compile src/llm/resilient_gateway.py`
- **完了条件**: Prometheusカウンタ呼び出しが記述されていること。

### Step 8: 管理用プロバイダ状態取得API `GET /admin/llm/providers/status` の実装
- **目的**: 現在各プロバイダのサーキット状態（CLOSED/OPEN/HALF-OPEN）や最近のエラー理由をリアルタイムに確認できるエンドポイント。
- **対象ファイル**: `src/backend/routers/system.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/system.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 9: 管理用サーキット手動リセットAPI `POST /admin/llm/circuit-breaker/reset` の実装
- **目的**: 外部障害が復旧した際、手動でサーキットを即座に CLOSED に戻す管理者エンドポイント。
- **対象ファイル**: `src/backend/routers/system.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/system.py`
- **完了条件**: リセットエンドポイントが追加されていること。

### Step 10: 既存 `UltimateHegemonyEngine` への `ResilientLLMGateway` 統合
- **目的**: メインエンジンの直接LLM呼び出し部分を `ResilientLLMGateway` 経由にリファクタリング。
- **対象ファイル**: `src/backend/engine.py`
- **変更内容**: `self.llm_gateway = ResilientLLMGateway(...)` を使用。
- **確認コマンド**: `python -m py_compile src/backend/engine.py`
- **完了条件**: エンジンがコンパイルできること。

### Step 11: サーキットブレーカー & フェイルオーバーの単体テスト作成
- **目的**: プロバイダ連続失敗 ➔ 自動遮断 ➔ 代替プロバイダでの正常応答 ➔ クールダウン後の復旧をシミュレーション検証。
- **対象ファイル**: `tests/unit/test_llm_resilient_gateway.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_llm_resilient_gateway.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 12: 【Checkpoint 1】Part 1 フェイルオーバー動作確認
- **目的**: LLM堅牢性ゲートウェイの単体テストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_llm_resilient_gateway.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 💰 Part 2: トークン予算・APIコスト監視ガード & 自動モデルダウングレード (Step 13〜24)

### Step 13: プロバイダ・モデル別トークン単価テーブルの定義
- **目的**: 1,000トークンあたりの入力・出力コスト（ドル/円）を外部定義し、正確なコスト計算を行う。
- **対象ファイル**: `config/model_pricing.yaml` (新規作成)
- **変更内容**:
  ```yaml
  pricing:
    anthropic/claude-3-5-sonnet:
      input_per_1k: 0.003
      output_per_1k: 0.015
    openai/gpt-4o:
      input_per_1k: 0.0025
      output_per_1k: 0.010
    openai/gpt-4o-mini:
      input_per_1k: 0.00015
      output_per_1k: 0.0006
    google/gemini-1.5-flash:
      input_per_1k: 0.000075
      output_per_1k: 0.0003
  ```
- **確認コマンド**: `python -c "import yaml; d = yaml.safe_load(open('config/model_pricing.yaml')); assert 'pricing' in d; print('OK')"`
- **完了条件**: YAMLが正常にパースできること。

### Step 14: コスト計算エンジン `CostCalculator` の実装
- **目的**: 消費された入力トークン数・出力トークン数・モデル名から、リアルタイムの消費コスト（USD/JPY）を算出。
- **対象ファイル**: `src/services/cost_analytics.py`
- **確認コマンド**: `python -c "from src.services.cost_analytics import CostCalculator; calc = CostCalculator(); print('OK')"`
- **完了条件**: 計算エンジンがインポートできること。

### Step 15: 予算監視ガードクラス `CostBudgetGuard` の実装
- **目的**: 日次・月次・作品ごとの予算上限（例: 1作品あたり最大 $5.00）を監視し、危険水域を検知するガード。
- **対象ファイル**: `src/services/cost_budget_guard.py` (新規作成)
- **変更内容**:
  ```python
  class CostBudgetGuard:
      def check_budget_status(self, book_id: int) -> BudgetStatus:
          # NORMAL (70%未満), WARNING (70-90%), EXCEEDED (100%超)
          ...
  ```
- **確認コマンド**: `python -m py_compile src/services/cost_budget_guard.py`
- **完了条件**: クラスが定義されていること。

### Step 16: 予算超過時の自動モデルダウングレード（廉価モデルルーティング）
- **目的**: 予算警告（90%超）または超過（100%超）時に、大型モデル（Claude 3.5 Sonnet 等）から高速廉価モデル（GPT-4o-mini, Gemini 1.5 Flash）へ自動で切り替え、完全停止を防ぎつつコストを抑制。
- **対象ファイル**: `src/services/cost_budget_guard.py`
- **変更内容**: `get_recommended_model_for_task(task_type, book_id)` の実装。
- **確認コマンド**: `python -m py_compile src/services/cost_budget_guard.py`
- **完了条件**: ダウングレードロジックが実装されていること。

### Step 17: 日次・作品別コスト集計テーブル `cost_consumption_logs` の追加
- **目的**: どのエージェントがどのモデルで何トークン消費し、いくら費用が発生したかを詳細記録するDBモデル。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**: `CostLogModel`（book_id, chapter_number, agent_name, model_name, input_tokens, output_tokens, cost_usd, timestamp）。
- **確認コマンド**: `python -c "from src.backend.database.models import CostLogModel; print('OK')"`
- **完了条件**: モデルが定義されていること。

### Step 18: Alembicマイグレーションスクリプト作成 (`0024_cost_consumption_logs.py`)
- **目的**: `cost_consumption_logs` テーブルを作成。
- **対象ファイル**: `database/alembic/versions/0024_cost_consumption_logs.py`
- **確認コマンド**: `python -m py_compile database/alembic/versions/0024_cost_consumption_logs.py`
- **完了条件**: コンパイルできること。

### Step 19: トークントラッカーと `CostLogModel` の非同期自動記録フック
- **目的**: LLM呼び出し完了時に `token_tracker` から自動で `CostLogModel` へコミット。
- **対象ファイル**: `src/services/token_tracker.py`
- **確認コマンド**: `python -m py_compile src/services/token_tracker.py`
- **完了条件**: コミットフックが組み込まれていること。

### Step 20: 予算設定・状況取得API `GET /api/cost/budget/{book_id}` の実装
- **目的**: 現在の消費金額、上限予算、現在のダウングレード状態を返却するエンドポイント。
- **対象ファイル**: `src/backend/routers/cost.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/cost.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 21: 予算上限更新API `POST /api/cost/budget/{book_id}` の実装
- **目的**: ユーザーが作品ごとの上限金額（例: $10.00）を変更・設定できるエンドポイント。
- **対象ファイル**: `src/backend/routers/cost.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/cost.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 22: フロントエンド Studio 画面ヘッダーへの「消費コスト（$）」インジケーター表示
- **目的**: 現在の作品の累計APIコストを `$0.42 / $5.00` のようにリアルタイム表示し、コストの透明性を担保。
- **対象ファイル**: `frontend/src/components/studio/StudioWorkspace.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: インジケーターが組み込まれていること。

### Step 23: コスト監視・自動ダウングレード機能の単体テスト作成
- **目的**: 予算閾値超過時に正しく小型モデルへルーティングが切り替わるかを検証。
- **対象ファイル**: `tests/unit/test_cost_budget_guard.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_cost_budget_guard.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 24: 【Checkpoint 2】Part 2 コストガード動作確認
- **目的**: コスト計算とダウングレードロジックの単体テストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_cost_budget_guard.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 🕸️ Part 3: SQLite/スタンドアロン環境向け NetworkX グラフ探索の完全等価化 (Step 25〜36)

### Step 25: グラフ抽象インターフェース `GraphKnowledgeStore` の拡張
- **目的**: Apache AGE（PostgreSQL）と NetworkX（Pure Python/SQLite）の共通操作を定義。
- **対象ファイル**: `src/services/graph/base.py` (新規作成)
- **変更内容**: `add_entity()`, `add_relation()`, `find_neighbors(entity_id, hops=2)`, `find_shortest_path()`, `get_centrality()` を抽象定義。
- **確認コマンド**: `python -c "from src.services.graph.base import GraphKnowledgeStore; print('OK')"`
- **完了条件**: 抽象基底クラスがインポートできること。

### Step 26: Pure Python / NetworkX グラフエンジン `NetworkXGraphStore` の新設
- **目的**: PostgreSQL や Apache AGE 拡張が一切ないローカル環境（Windowsバッチ起動やSQLite環境）でも、高速なマルチ有向グラフ（`nx.MultiDiGraph`）探索を提供する。
- **対象ファイル**: `src/services/graph/networkx_store.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/services/graph/networkx_store.py`
- **完了条件**: コンパイルできること。

### Step 27: NetworkX グラフデータの SQLite 永続化（シリアライズ・デシリアライズ）
- **目的**: アプリケーション再起動時にもインメモリグラフが消失しないよう、SQLiteテーブル `graph_nodes` および `graph_edges` と相互変換。
- **対象ファイル**: `src/services/graph/networkx_store.py`
- **変更内容**: `save_to_sqlite(db)` および `load_from_sqlite(db)` の実装。
- **確認コマンド**: `python -m py_compile src/services/graph/networkx_store.py`
- **完了条件**: 永続化処理が実装されていること。

### Step 28: Cypher風 簡易クエリパーサー `CypherToNetworkXTranslator` の実装
- **目的**: 既存の `MATCH (c:Character)-[:FRIEND]->(t)` 形式のクエリを、NetworkX のノード・エッジ走査コードに透過的に変換。
- **対象ファイル**: `src/services/graph/cypher_translator.py` (新規作成)
- **確認コマンド**: `python -c "from src.services.graph.cypher_translator import CypherToNetworkXTranslator; print('OK')"`
- **完了条件**: トランスレーターがインポートできること。

### Step 29: 2-hop 近傍探索および関係パス抽出の NetworkX 完全等価実装
- **目的**: Apache AGE で実行されていた「指定キャラクターから2ホップ以内の人間関係・アイテム探索」を NetworkX で同一結果を返すように実装。
- **対象ファイル**: `src/services/graph/networkx_store.py`
- **確認コマンド**: `python -m py_compile src/services/graph/networkx_store.py`
- **完了条件**: 2-hop探索関数が実装されていること。

### Step 30: PageRank / 次数中心性スコア算出の NetworkX 最適化
- **目的**: 4層コンテキスト圧縮 Layer 3 で使用される「エンティティ中心性重要度」を `nx.pagerank` で高速計算。
- **対象ファイル**: `src/services/graph/networkx_store.py`
- **確認コマンド**: `python -m py_compile src/services/graph/networkx_store.py`
- **完了条件**: 中心性計算が実装されていること。

### Step 31: ハイブリッド・グラフファサード `HybridGraphFacade` の実装
- **目的**: `ENABLE_GRAPHRAG=true` かつ PostgreSQL/AGE 接続可能なら AGE を使用し、接続不可または SQLite 時は自動で `NetworkXGraphStore` にフォールバックするファサード。
- **対象ファイル**: `src/services/graph/hybrid_graph_facade.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/services/graph/hybrid_graph_facade.py`
- **完了条件**: ファサードがコンパイルできること。

### Step 32: 既存 `AgeClient` から `HybridGraphFacade` への委譲リファクタリング
- **目的**: `src/services/age_client.py` の内部実装を `HybridGraphFacade` に委譲し、呼び出し元の後方互換性を100%維持。
- **対象ファイル**: `src/services/age_client.py`
- **確認コマンド**: `python -m py_compile src/services/age_client.py`
- **完了条件**: 後方互換を保ちコンパイルできること。

### Step 33: ナレッジグラフ可視化API `GET /api/graph/{book_id}/visualization` の等価対応
- **目的**: NetworkX 保持データからフロントエンド（Force Graph）用の `{ nodes: [...], links: [...] }` JSON を同一構造で返却。
- **対象ファイル**: `src/backend/routers/graph.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/graph.py`
- **完了条件**: 可視化APIが更新されていること。

### Step 34: ナレッジグラフ手動ノード・エッジ編集API (CRUD) の追加
- **目的**: フロントエンドから直接「新しい登場人物ノード」や「敵対エッジ」を追加・編集・削除できるエンドポイントを追加。
- **対象ファイル**: `src/backend/routers/graph.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/graph.py`
- **完了条件**: CRUDエンドポイントが追加されていること。

### Step 35: NetworkX グラフエンジンの単体・等価性テスト作成
- **目的**: ノード追加、関係性作成、2-hop探索、中心性計算が正確に行われるかをテスト。
- **対象ファイル**: `tests/unit/test_networkx_graph_store.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_networkx_graph_store.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 36: 【Checkpoint 3】Part 3 グラフエンジン動作検証
- **目的**: NetworkX グラフエンジンの単体テストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_networkx_graph_store.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## ⚡ Part 4: 8専門オーディターのLLM動的インテリジェント・ルーティング (Step 37〜48)

### Step 37: オーディター特性別モデル割り当て設定 `config/audit_models.yaml` の新設
- **目的**: 8人の専門オーディターのタスク難易度に応じて、推論モデルを個別設定するマッピングファイルを作成。
- **対象ファイル**: `config/audit_models.yaml` (新規作成)
- **変更内容**:
  ```yaml
  auditor_models:
    # 事実照合・誤字・整合性チェックは高速・廉価なモデルで十分
    factual: "google/gemini-1.5-flash"
    consistency: "google/gemini-1.5-flash"
    style: "google/gemini-1.5-flash"
    multimodal: "google/gemini-1.5-flash"
    
    # 高度な心理分析・起承転結・読者心理の推論には大型知性モデルを充当
    creativity: "anthropic/claude-3-5-sonnet-20241022"
    reader_hook: "anthropic/claude-3-5-sonnet-20241022"
    emotion_curve: "anthropic/claude-3-5-sonnet-20241022"
    structure: "openai/gpt-4o"
  ```
- **確認コマンド**: `python -c "import yaml; d = yaml.safe_load(open('config/audit_models.yaml')); assert 'auditor_models' in d; print('OK')"`
- **完了条件**: YAMLが正常にパースできること。

### Step 38: モデルルータークラス `AuditorModelRouter` の実装
- **目的**: 専門家名（例: `creativity`）を受け取り、設定ファイルに基づき適切なLLMクライアント/プロバイダインスタンスを返すルーター。
- **対象ファイル**: `src/agents/specialists/model_router.py` (新規作成)
- **確認コマンド**: `python -c "from src.agents.specialists.model_router import AuditorModelRouter; print('OK')"`
- **完了条件**: ルータークラスがインポートできること。

### Step 39: `SpecialistAuditor` 基底クラスへの動的モデル解決の統合
- **目的**: 各専門オーディターが実行時に `self.model_router.get_llm_for_auditor(self.auditor_name)` を自動取得するよう改修。
- **対象ファイル**: `src/agents/specialist_auditor_base.py`
- **確認コマンド**: `python -m py_compile src/agents/specialist_auditor_base.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 40: 8オーディター並列実行時のセマフォ（同時実行数制限）導入
- **目的**: 8エージェントが一斉にAPIを叩いてレートリミット（429）を踏むのを防止するため、`asyncio.Semaphore(concurrency=4)` によるスロットリングを導入。
- **対象ファイル**: `src/services/audit_aggregator.py`
- **確認コマンド**: `python -m py_compile src/services/audit_aggregator.py`
- **完了条件**: セマフォ制御が組み込まれていること。

### Step 41: 軽量オーディター群のバッチ推論（一括問い合わせ）最適化
- **目的**: `factual`, `consistency`, `style` の3つを1回のプロンプトで同時に評価可能な「高速バッチモード」の選択肢を追加。
- **対象ファイル**: `src/services/audit_aggregator.py`
- **確認コマンド**: `python -m py_compile src/services/audit_aggregator.py`
- **完了条件**: バッチモードが実装されていること。

### Step 42: 設定ファイル動的再読み込み（ホットリロード）機能
- **目的**: アプリケーション再起動なしで `config/audit_models.yaml` の変更を即時反映するリフレッシュメソッドの実装。
- **対象ファイル**: `src/agents/specialists/model_router.py`
- **確認コマンド**: `python -m py_compile src/agents/specialists/model_router.py`
- **完了条件**: リロード機能が実装されていること。

### Step 43: 管理API `GET /admin/audit/model-routing` の新設
- **目的**: 現在どの専門オーディターにどのモデルが割り当てられているかを一覧返却。
- **対象ファイル**: `src/backend/routers/system.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/system.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 44: 管理API `POST /admin/audit/model-routing` の新設
- **目的**: 管理画面から動的にオーディターのモデル割り当てを変更可能にする。
- **対象ファイル**: `src/backend/routers/system.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/system.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 45: 監査トークン消費量・コスト削減率の Prometheus メトリクス計測
- **目的**: 一律大型モデル適用時と比較したコスト削減率をメトリクス `audit_cost_savings_ratio` として記録。
- **対象ファイル**: `src/services/audit_aggregator.py`
- **確認コマンド**: `python -m py_compile src/services/audit_aggregator.py`
- **完了条件**: メトリクス記録が記述されていること。

### Step 46: モデルルーターの単体テスト作成
- **目的**: 各オーディターに対して指定通りのモデルが取得されること、ホットリロードが機能することを検証。
- **対象ファイル**: `tests/unit/test_auditor_model_router.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_auditor_model_router.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 47: 8オーディター並列監査の実行コスト削減検証テスト
- **目的**: 動的ルーティング適用時と全Sonnet適用時で、生成コストが70%以上削減されることをシミュレーション検証。
- **対象ファイル**: `tests/unit/test_audit_routing_cost.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_audit_routing_cost.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 48: 【Checkpoint 4】Part 4 オーディター動的ルーティング動作検証
- **目的**: モデルルーターおよび並列監査テストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_auditor_model_router.py tests/unit/test_audit_routing_cost.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 🔄 Part 5: 障害自己修復 & ワーカークラッシュ時の自動リジューム (WAL/Checkpoints) (Step 49〜60)

### Step 49: タスク実行Write-Ahead Log (WAL) 記録モデル `TaskWALLogModel` の定義
- **目的**: 各DAGタスクの「実行開始」「入力パラメータ」「中間状態」「完了/失敗」を追記専用ログとしてDBに永続化。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**: `TaskWALLogModel`（task_id, dag_id, node_id, state, input_json, output_json, heartbeat_at, created_at）。
- **確認コマンド**: `python -c "from src.backend.database.models import TaskWALLogModel; print('OK')"`
- **完了条件**: モデルが定義されていること。

### Step 50: Alembicマイグレーションスクリプト作成 (`0025_task_wal_logs.py`)
- **目的**: `task_wal_logs` テーブルを作成。
- **対象ファイル**: `database/alembic/versions/0025_task_wal_logs.py`
- **確認コマンド**: `python -m py_compile database/alembic/versions/0025_task_wal_logs.py`
- **完了条件**: コンパイルできること。

### Step 51: ワーカーハートビート更新機構の実装
- **目的**: 長時間タスク実行中、ワーカーが30秒ごとに `heartbeat_at` を更新し、プロセス死活を判定可能にする。
- **対象ファイル**: `src/backend/tasks/worker_recovery.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/backend/tasks/worker_recovery.py`
- **完了条件**: ハートビート関数が実装されていること。

### Step 52: 孤立・ゾンビタスク（Orphan Tasks）の検知ロジック
- **目的**: `state == 'running'` かつ `heartbeat_at` が5分以上途絶えているタスクを「クラッシュにより中断」と判定。
- **対象ファイル**: `src/backend/tasks/worker_recovery.py`
- **確認コマンド**: `python -m py_compile src/backend/tasks/worker_recovery.py`
- **完了条件**: ゾンビ検知ロジックが実装されていること。

### Step 53: ゾンビタスクの安全なリカバリ・再スケジュール機構
- **目的**: 中断されたタスクを `state='pending'` に戻し、下流タスクを一時停止した上で自動再スケジュール。
- **対象ファイル**: `src/backend/tasks/worker_recovery.py`
- **変更内容**: `recover_orphan_tasks(db)` メソッド。
- **確認コマンド**: `python -m py_compile src/backend/tasks/worker_recovery.py`
- **完了条件**: リカバリ処理が実装されていること。

### Step 54: DAGスケジューラ起動時の「自動リジューム（復帰）」フック
- **目的**: サーバー再起動時やHueyワーカー起動時に、直前の未完了DAGをスキャンして自動復帰させる。
- **対象ファイル**: `src/backend/tasks/dag_scheduler.py`
- **変更内容**: `on_startup` ハンドラで `WorkerRecoveryManager.resume_all_active_dags()` を呼び出す。
- **確認コマンド**: `python -m py_compile src/backend/tasks/dag_scheduler.py`
- **完了条件**: 起動時フックが記述されていること。

### Step 55: 中間チェックポイントからの再開（冪等性の担保）
- **目的**: 執筆完了後に挿絵生成タスクでクラッシュした場合、執筆をやり直さず「挿絵ノード」からピンポイントで再開。
- **対象ファイル**: `src/backend/tasks/dag_scheduler.py`
- **変更内容**: 完了済み先行ノードの出力をWALから復元して下流ノードに供給。
- **確認コマンド**: `python -m py_compile src/backend/tasks/dag_scheduler.py`
- **完了条件**: チェックポイント再開ロジックが実装されていること。

### Step 56: 最大クラッシュリカバリ試行回数（Poison Pill 防止）
- **目的**: コードのバグやOOMで何度再開しても確実にクラッシュするタスクを最大3回で打ち切り、DAG全体が無限ループするのを防ぐ。
- **対象ファイル**: `src/backend/tasks/worker_recovery.py`
- **確認コマンド**: `python -m py_compile src/backend/tasks/worker_recovery.py`
- **完了条件**: 上限保護が記述されていること。

### Step 57: リカバリ発生時の管理者アラートログ発行
- **目的**: ワーカークラッシュおよび自動復旧の発生をログおよびイベントバスへ通知。
- **対象ファイル**: `src/backend/tasks/worker_recovery.py`
- **確認コマンド**: `python -m py_compile src/backend/tasks/worker_recovery.py`
- **完了条件**: アラート発行が記述されていること。

### Step 58: 管理API `POST /admin/tasks/recover` の新設
- **目的**: 手動で孤立タスクの監査とリカバリを即座にトリガーできるエンドポイント。
- **対象ファイル**: `src/backend/routers/tasks.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/tasks.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 59: ワーカーリカバリマネージャの単体テスト作成
- **目的**: ゾンビタスクの検知、チェックポイントからの再開、上限打ち切りが正しく動作するかをテスト。
- **対象ファイル**: `tests/unit/test_worker_recovery.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_worker_recovery.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 60: 【Checkpoint 5】Part 5 自動リカバリ機能動作検証
- **目的**: リカバリマネージャ単体テストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_worker_recovery.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 🧪 Part 6: カオスエンジニアリング検証 & 第3段階 E2E 包括的回帰テスト (Step 61〜72)

### Step 61: カオス障害注入ユーティリティ `ChaosInjector` の作成
- **目的**: テスト実行中にランダムなLLM API例外（500, 429）、Redis切断、ワーカー突然死を意図的に引き起こすヘルパー。
- **対象ファイル**: `tests/fixtures/chaos_injector.py` (新規作成)
- **確認コマンド**: `python -c "from tests.fixtures.chaos_injector import ChaosInjector; print('OK')"`
- **完了条件**: ヘルパーがインポートできること。

### Step 62: カオステスト 1（主LLM突然死時の自動フェイルオーバー検証）
- **目的**: 本文執筆中に主プロバイダ（Claude）を突然停止させ、数ミリ秒でGPT-4o/Geminiへ迂回して正常完結することを実証。
- **対象ファイル**: `tests/integration/test_chaos_llm_failover.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_chaos_llm_failover.py -v`
- **完了条件**: テストが PASS すること。

### Step 63: カオステスト 2（ワーカー強制終了後のチェックポイント自動復帰検証）
- **目的**: 長編生成DAGの途中でプロセスを `SIGKILL` 相当で終了させ、再起動後に中断ノードから100%復旧することを実証。
- **対象ファイル**: `tests/integration/test_chaos_worker_resume.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_chaos_worker_resume.py -v`
- **完了条件**: テストが PASS すること。

### Step 64: カオステスト 3（予算上限到達時の自動モデルダウングレード検証）
- **目的**: 大量リクエストを送り予算上限に達した瞬間、後続タスクが廉価モデルへ安全に移行することを実証。
- **対象ファイル**: `tests/integration/test_chaos_budget_downgrade.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_chaos_budget_downgrade.py -v`
- **完了条件**: テストが PASS すること。

### Step 65: NetworkX と Apache AGE のグラフクエリ結果同一性ベンチマークテスト
- **目的**: 1,000ノードの巨大世界観グラフにおいて、AGEとNetworkXが同一の近傍探索結果と中心性順位を返すことを実証。
- **対象ファイル**: `tests/benchmarks/test_graph_equivalence_benchmark.py` (新規作成)
- **確認コマンド**: `pytest tests/benchmarks/test_graph_equivalence_benchmark.py -v`
- **完了条件**: テストが PASS すること。

### Step 66: 8専門オーディター動的ルーティングの全結合E2Eテスト
- **目的**: 全8専門家がそれぞれの最適化モデルで並列実行され、BookScore算出および特化ディレクティブが生成される完全フローをテスト。
- **対象ファイル**: `tests/integration/test_phase3_auditor_routing_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase3_auditor_routing_e2e.py -v`
- **完了条件**: テストが PASS すること。

### Step 67: 第3段階 包括的長編自律生成E2Eテスト
- **目的**: 企画 ➔ 逆算プロット ➔ 10話連続生成 ➔ 8オーディター並列監査 ➔ PDCA自動再執筆 ➔ 挿絵生成 ➔ 商用EPUB納品が、一切のエラー・停止なく完遂することを実証。
- **対象ファイル**: `tests/integration/test_phase3_autonomous_novel_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase3_autonomous_novel_e2e.py -v`
- **完了条件**: E2Eテストが PASS すること。

### Step 68: システム健全性・オブザーバビリティ全チェック
- **目的**: `/health`, `/metrics`, `/admin/llm/providers/status`, `/admin/cost/budget` の全診断エンドポイントが正常応答することを確認。
- **対象ファイル**: `scripts/health_check_phase3.py` (新規作成)
- **確認コマンド**: `python scripts/health_check_phase3.py`
- **完了条件**: 全項目 OK で終了すること。

### Step 69: 第3段階 アーキテクチャガイドの整備
- **目的**: フェイルオーバー設計、NetworkXフォールバック、コストガード、障害復旧仕様を公式ドキュメントへ追記。
- **対象ファイル**: `docs/ARCHITECTURE_RESILIENCE.md` (新規作成)
- **確認コマンド**: `python -c "from pathlib import Path; assert Path('docs/ARCHITECTURE_RESILIENCE.md').exists(); print('OK')"`
- **完了条件**: ドキュメントが存在すること。

### Step 70: コードベース全体のクリーンアップと型チェック
- **目的**: 全Pythonファイルの構文コンパイル、Ruffチェック、MyPy型チェック。
- **確認コマンド**: `python -m ruff check src/ tests/ && python -m py_compile src/backend/server.py`
- **完了条件**: エラー0件であること。

### Step 71: フロントエンド本番ビルドの最終疎通検証
- **目的**: バックエンドのAPI変更に伴うフロントエンド側の型不整合がないか最終確認。
- **確認コマンド**: `npm run --prefix frontend typecheck && npm run --prefix frontend build`
- **完了条件**: ビルドが正常に完了すること。

### Step 72: 【Final Gate】全段階 包括的総合回帰テスト (100% ALL GREEN)
- **目的**: 第1段階〜第3段階で追加された全テストスイートおよびAutoNovelの既存全テストを一括実行し、完全動作を保証する。
- **確認コマンド**: `pytest tests/unit/test_llm_resilient_gateway.py tests/unit/test_cost_budget_guard.py tests/unit/test_networkx_graph_store.py tests/unit/test_auditor_model_router.py tests/unit/test_worker_recovery.py tests/integration/test_chaos_llm_failover.py tests/integration/test_phase3_autonomous_novel_e2e.py -v -o "addopts="`
- **完了条件**: すべてのテストがオールグリーン（ALL GREEN）であること。
