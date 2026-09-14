# PLAN 18: Prompt Caching完全適用＆3層ハイブリッドルーティング（原価90%削減） 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 LLMゲートウェイ、プロンプト構築層、コスト最適化基盤 (`src/services/llm_service.py`, `src/llm/model_router.py`)  
**目的**: 1エピソードあたり約64〜150円かかっていたLLM API原価を、**「Anthropic Prompt Cachingの徹底適用」** と **「タスク難易度に応じた3層ハイブリッドモデルルーティング」** により **8〜15円（約90%削減）** へ圧縮し、商用SaaSとしての黒字化と高利益率を確立する。  
**前提**: 小説のクライマックスや重要シーンの文学的品質（Claude 3.5 Sonnet水準）を一切落とさずに、周辺タスク（構成・監査・日常ドラフト）のコストを極限まで削ぎ落とす。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | 設定定義 | `src/config/cost_optimization.py` (新規) | モデル別単価マトリクス、3層ルーティング規則、キャッシュTTL定義 |
| **2** | キャッシュ構築 | `src/services/llm/prompt_cache_builder.py` (新規) | 世界観Bible・キャラ設定をAnthropic/OpenAIのキャッシュブロックへ自動パッキング |
| **3** | Claude統合 | `src/infrastructure/external/anthropic_client.py` (修正) | `cache_control: {"type": "ephemeral"}` を用いたPrompt Caching完全対応 |
| **4** | 3層ルーター | `src/llm/model_router.py` (修正) | Tier 1 (Flash), Tier 2 (Haiku), Tier 3 (Sonnet) の動的振り分けロジック |
| **5** | シーン判定 | `src/services/narrative/scene_tier_evaluator.py` (新規) | プロットのTension/Catharsis値から「日常回(Tier2)」か「クライマックス(Tier3)」か判定 |
| **6** | フェイルオーバー | `src/services/llm/provider_failover.py` (新規) | 429（レート制限）や503障害時に別プロバイダ（OpenAI/Gemini/Claude）へ自動迂回 |
| **7** | コスト計測 | `src/services/observability/token_cost_tracker.py` (新規) | リクエストごとの入力/出力/キャッシュヒットトークン数と実円コストの精密計測 |
| **8** | DB記録 | `src/backend/database/models.py` (修正) | `Episode` テーブルに `cost_jpy`, `cache_hit_ratio` カラムを追加 |
| **9** | ゲートウェイ統合 | `src/services/llm_service.py` (修正) | キャッシュビルダー、3層ルーター、コスト計測を包括する統合ファサード化 |
| **10** | バックエンドAPI | `src/backend/routers/cost.py` (修正) | 作品別・ユーザー別の累計消費コスト・削減額・キャッシュ効果レポートAPI |
| **11** | 管理UI | `frontend/src/components/admin/CostAnalyticsDashboard.tsx` (新規) | キャッシュヒット率、1話あたりの平均原価推移、利益率を可視化する管理画面 |
| **12** | 統合検証 | `tests/unit/test_prompt_caching_and_router.py` (新規) | キャッシュヘッダー付与、シーン別モデル振り分け、コスト90%削減効果の単体テスト |

---

## 各ステップの詳細仕様

### Step 1: コスト最適化マトリクス定義 (`src/config/cost_optimization.py`)
* **目標**: モデル別トークン単価とルーティングポリシーを一元管理。
* **実装内容**:
  ```python
  from pydantic import BaseModel

  # 1MトークンあたりのUSD単価 (2026年時点想定)
  MODEL_PRICING = {
      "gemini-2.0-flash": {"input": 0.10, "output": 0.40, "cached_input": 0.025},
      "claude-3-5-haiku": {"input": 0.80, "output": 4.00, "cached_input": 0.08},
      "claude-3-5-sonnet": {"input": 3.00, "output": 15.00, "cached_input": 0.30},
      "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cached_input": 0.075},
  }

  ROUTING_TIERS = {
      "tier1_light": "gemini-2.0-flash",      # 構成・ブレスト・要約・監査
      "tier2_standard": "claude-3-5-haiku",   # 日常シーン・展開回の執筆
      "tier3_premium": "claude-3-5-sonnet",   # クライマックス・第1話・重要伏線回収
  }
  ```
* **受け入れ基準**: 各種単価とティア定義が静的型定義されていること。

---

### Step 2: Prompt Cache ビルダー (`src/services/llm/prompt_cache_builder.py`)
* **目標**: 静的コンテキスト（Bible、キャラ設定）を動的プロンプトの先頭に配置しキャッシュブロック化。
* **実装内容**:
  - 変更頻度の低い「世界観設定（Bible）」と「主要キャラクター辞書」を構造化。
  - 最低トークン要件（Anthropicは1,024トークン以上でキャッシュ有効）を満たすようパッキング。
* **受け入れ基準**: システムプロンプト部分がキャッシュ対象ブロックとして正しく分離されること。

---

### Step 3: Anthropic Prompt Caching 統合 (`src/infrastructure/external/anthropic_client.py`)
* **目標**: Anthropic Messages API の `cache_control` を正式利用。
* **実装内容**:
  ```python
  # Anthropic SDK 呼び出し
  system_payload = [
      {
          "type": "text",
          "text": world_bible_context,
          "cache_control": {"type": "ephemeral"}  # キャッシュ有効化
      }
  ]
  ```
* **受け入れ基準**: レスポンスヘッダーの `cache_read_input_tokens` が取得でき、2回目以降に読み取りトークンがカウントされること。

---

### Step 4: 3層タスクルーター拡張 (`src/llm/model_router.py`)
* **目標**: リクエストの要求品質とタスク種別から最適モデルを動的解決。
* **実装内容**:
  ```python
  def resolve_optimized_model(task_type: str, is_climax: bool = False, user_plan: str = "free") -> str:
      if task_type in ["planning", "audit", "screening"]:
          return ROUTING_TIERS["tier1_light"]
      if is_climax or user_plan in ["pro", "enterprise"]:
          return ROUTING_TIERS["tier3_premium"]
      return ROUTING_TIERS["tier2_standard"]
  ```
* **受け入れ基準**: タスクとシーン重要度に応じて適切なモデルIDが即座に解決されること。

---

### Step 5: シーン重要度エバリュエーター (`src/services/narrative/scene_tier_evaluator.py`)
* **目標**: 第1話、中盤大どんでん返し、最終回を自動検知してTier 3モデルを適用。
* **実装内容**:
  - `PlotDbModel.tension >= 80` または `is_catharsis == True` または `ep_num in [1, mid_point, last]` の場合にクライマックス判定。
* **受け入れ基準**: 重要なカタルシス回のみが自動的にTier 3（Sonnet）へと昇格すること。

---

### Step 6: プロバイダ自動フェイルオーバー (`src/services/llm/provider_failover.py`)
* **目標**: OpenAI/Anthropic/GoogleのAPI障害時に執筆を停止させない。
* **実装内容**:
  - 指数バックオフリトライ（最大3回）。
  - レート制限（429）やサーバー障害（500/503）検知時に、別プロバイダの同等モデルへ自動フォールバック。
* **受け入れ基準**: 1つのプロバイダがダウンしてもユーザーにエラー画面が出ず生成が完了すること。

---

### Step 7: 実トークンコスト計測トラッカー (`src/services/observability/token_cost_tracker.py`)
* **目標**: 1リクエストごとの実コストを日本円換算で正確に集計。
* **実装内容**:
  - `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` から計算。
  - キャッシュによって浮いた削減金額（Saved JPY）も同時に算出。
* **受け入れ基準**: API呼び出し完了時にミリ秒単位の所要時間と円建てコストが算出されること。

---

### Step 8: ORMモデルへのコスト記録カラム追加 (`src/backend/database/models.py`)
* **目標**: エピソードごとに実際にかかった原価をDBに記録。
* **実装内容**:
  - `Episode` テーブルに `cost_jpy = Column(Float, default=0.0)`, `saved_jpy = Column(Float, default=0.0)` を追加。
* **受け入れ基準**: 各話の生成完了時に実コストがDBに永続化されること。

---

### Step 9: LLM統合ファサードの改修 (`src/services/llm_service.py`)
* **目標**: 既存コードの呼び出しインターフェースを維持したまま、キャッシュとルーターを自動適用。
* **実装内容**:
  - `generate_text()`, `generate_chapter()` が自動的にコストトラッカーとキャッシュビルダーを通るよう統合。
* **受け入れ基準**: 既存の呼び出し元コードを変更することなく、コスト削減ロジックが透過的に機能すること。

---

### Step 10: コスト分析APIエンドポイント (`src/backend/routers/cost.py`)
* **目標**: 管理者およびユーザーが削減実績を確認できるAPI。
* **実装内容**:
  - `GET /api/cost/summary`: 今月の総生成コスト、削減額、キャッシュヒット率（%）の返却。
* **受け入れ基準**: 正確な統計データJSONが返却されること。

---

### Step 11: コスト分析管理ダッシュボード (`frontend/src/components/admin/CostAnalyticsDashboard.tsx`)
* **目標**: 運営者がSaaSの採算性をリアルタイムに監視できるUI。
* **実装内容**:
  - 1話あたりの平均原価グラフ（目標: 15円以下）。
  - キャッシュヒット率ゲージ（目標: 80%以上）。
  - プラン別の粗利率（Gross Margin）表示。
* **受け入れ基準**: グラフが描画され、キャッシュ効果が一目で確認できること。

---

### Step 12: コスト削減統合テスト (`tests/unit/test_prompt_caching_and_router.py`)
* **目標**: キャッシュ適用時と非適用時のコスト差を単体テストで検証。
* **実装内容**:
  - 2回目の同一プロンプト実行時にキャッシュヒットトークンが計上されることを確認。
  - 全タスクをTier 3で実行した場合と、3層ハイブリッドで実行した場合のコスト差（約90%減）をシミュレーション検証。
* **受け入れ基準**: `pytest tests/unit/test_prompt_caching_and_router.py` が PASS すること。
