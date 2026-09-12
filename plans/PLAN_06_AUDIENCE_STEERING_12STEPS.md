# PLAN 06: 読者反応による動的プロット改変 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 プロット構築・フィードバック制御基盤  
**目的**: 連載中に寄せられるカクヨム読者の応援コメント、★評価、PV推移を感情分析し、「不人気キャラの早期退場」「人気ヒロインの出番前倒し」「ヘイト悪役への制裁加速」など、次話以降のプロットをリアルタイムに自動舵取り（Audience Steering）する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/audience_feedback.py` (新規) | 読者コメント、感情分析結果、プロット舵取り指示のPydanticモデル定義 |
| **2** | テスト | `tests/unit/audience/test_sentiment_analyzer.py` (新規) | 読者コメントの感情・要望抽出ロジックの単体テスト作成（TDD先行） |
| **3** | ロジック | `src/services/audience/sentiment_analyzer.py` (新規) | コメント群から「キャラ愛着」「不満・停滞感」「ざまぁ渇望」を定量化する分析機 |
| **4** | テスト | `tests/unit/audience/test_steering_rule_engine.py` (新規) | 感情分析結果からプロット変更ルールを発動するテスト作成 |
| **5** | ルール | `src/services/audience/steering_rule_engine.py` (新規) | 閾値判定に基づくプロット修正ディレクティブ生成ルールエンジン |
| **6** | プロンプト | `prompts/templates/audience/plot_steering_instruction.j2` (新規) | プロット再構築時に読者フィードバックを強制反映するJinja2プロンプト |
| **7** | 収集器 | `src/services/audience/feedback_collector.py` (新規) | カクヨム作品URLからコメント・★データを取得するコレクター（モック付） |
| **8** | プロット結合 | `src/agents/plot.py` (修正) | `PlotAgent` にステアリング指示を注入してプロットを部分再構築するメソッド追加 |
| **9** | ルーター | `src/backend/routers/audience_steering.py` (新規) | コメント分析実行・プロット修正プレビューFastAPIエンドポイント |
| **10** | 型定義 | `frontend/src/types/audience.ts` (新規) | フロントエンド用TypeScriptインターフェース |
| **11** | フロント | `frontend/src/components/audience/AudienceSteeringPanel.tsx` (新規) | 読者心理レーダーチャート＆プロット変更承認UIコンポーネント |
| **12** | 統合検証 | `tests/e2e/test_audience_steering_pipeline.py` (新規) | コメント投入から次話プロットのざまぁ前倒し確定までのE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/audience_feedback.py`)
* **目標**: 読者フィードバックと舵取り指示のデータ構造を定義。
* **実装内容**:
  ```python
  from pydantic import BaseModel, Field

  class ReaderCommentItem(BaseModel):
      ep_num: int
      author: str
      body: str

  class AudienceSentimentSummary(BaseModel):
      pacing_sentiment: str = Field(..., description="テンポ感 (ちょうどいい, 遅すぎる, 駆け足)")
      most_loved_character: str = Field(..., description="現在最も人気のあるキャラクター")
      hate_overflow_target: str = Field("", description="読者のヘイトが限界に達している敵キャラ")
      catharsis_hunger_score: float = Field(..., ge=0.0, le=100.0, description="ざまぁ・快感への渇望度")

  class PlotSteeringDirective(BaseModel):
      action_type: str = Field(..., description="REVISE_VILLAIN_FATE, PROMOTE_HEROINE, ACCELERATE_PACING 等")
      target_character: str
      instruction: str
      affected_episodes: list[int]
  ```
* **受け入れ基準**: `mypy src/models/audience_feedback.py` がエラーなく通ること。

---

### Step 2: 感情分析テスト作成 (`tests/unit/audience/test_sentiment_analyzer.py`)
* **目標**: コメント群から感情や読者の要望を正確に集約できるかテスト。
* **実装内容**:
  ```python
  import pytest
  from src.services.audience.sentiment_analyzer import analyze_audience_comments

  @pytest.mark.asyncio
  async def test_detect_hate_overflow():
      comments = [
          "あいつマジで胸糞悪い。早く消えてくれ",
          "早くざまぁが見たい！もう限界",
          "主人公はなんであいつを野放しにしてるの？イライラする",
      ]
      summary = await analyze_audience_comments(comments, mock_llm)
      assert summary.catharsis_hunger_score >= 80.0
      assert summary.pacing_sentiment in ("遅すぎる", "停滞")
  ```
* **受け入れ基準**: テストが正しく実行できること。

---

### Step 3: コメント感情分析エンジン (`src/services/audience/sentiment_analyzer.py`)
* **目標**: 読者コメントの生テキストから `AudienceSentimentSummary` を生成する。
* **実装内容**:
  - LLMを活用してコメント群のキーワード出現頻度とトーンを分類。
  - 「可愛い」「最高」→ ヒロイン好感度加点。
  - 「胸糞」「遅い」「イライラ」→ カタルシス渇望度加点。
* **受け入れ基準**: Step 2 のテストが GREEN になること。

---

### Step 4: ルールエンジン単体テスト (`tests/unit/audience/test_steering_rule_engine.py`)
* **目標**: 感情スコアに応じたプロット修正指示の発行ルールを検証。
* **実装内容**:
  - 渇望度80以上で「悪役制裁の前倒し」指示が発行されること。
  - 特定ヒロインへの言及が50%超で「出番増加」指示が発行されること。
* **受け入れ基準**: テストがモジュール未定義で正しく失敗すること。

---

### Step 5: ステアリングルールエンジン (`src/services/audience/steering_rule_engine.py`)
* **目標**: 感情サマリーをプロット変更アクションへ変換する。
* **実装内容**:
  ```python
  def evaluate_steering_rules(summary: AudienceSentimentSummary, current_ep: int) -> list[PlotSteeringDirective]:
      directives = []
      if summary.catharsis_hunger_score >= 75.0 and summary.hate_overflow_target:
          directives.append(PlotSteeringDirective(
              action_type="ACCELERATE_CATHARSIS",
              target_character=summary.hate_overflow_target,
              instruction=f"読者のヘイトが限界です。第{current_ep + 1}話〜第{current_ep + 2}話で{summary.hate_overflow_target}への完全な社会的断罪・ざまぁを断行してください。",
              affected_episodes=[current_ep + 1, current_ep + 2]
          ))
      return directives
  ```
* **受け入れ基準**: Step 4 のテストが通過すること。

---

### Step 6: プロット舵取りプロンプト (`prompts/templates/audience/plot_steering_instruction.j2`)
* **目標**: プロット再構築時に、読者の声による指示を最優先制約として注入するテンプレート。
* **実装内容**:
  - 指示: 「【緊急舵取り指示】読者からの反響に基づき、以下の展開変更を強制適用せよ: {{ directive.instruction }}」
  - 指示: 「既存の伏線や世界観と破綻しないよう、因果関係を自然に繋ぎ直せ」
* **受け入れ基準**: テンプレートレンダリングが構文エラーなく動作すること。

---

### Step 7: フィードバック収集器 (`src/services/audience/feedback_collector.py`)
* **目標**: カクヨムから最新コメントを取得する機能（開発・テスト用モック付き）。
* **実装内容**:
  - `fetch_latest_comments(work_id: str, limit: int = 50) -> list[ReaderCommentItem]`
  - モックモード時はリアルなカクヨム風コメントサンプル（ざまぁ希望、ヒロイン推し等）を生成。
* **受け入れ基準**: コメントリストが安定して取得できること。

---

### Step 8: PlotAgent連携 (`src/agents/plot.py`)
* **目標**: `PlotAgent` に `apply_audience_steering(book_id, directives)` を追加。
* **実装内容**:
  - 対象話数のプロット詳細（`PlotEpisode`）を読み込み、ステアリング指示を注入してプロットのみ再生成・DB更新。
* **受け入れ基準**: 指定話数のプロット要約が更新されること。

---

### Step 9: FastAPIルーター (`src/backend/routers/audience_steering.py`)
* **目標**: フロントエンドと連携するエンドポイントを開設。
* **実装内容**:
  - `POST /api/audience/analyze`: コメントを投入して感情サマリー取得
  - `POST /api/audience/directives`: 感情サマリーから舵取り指示を生成
  - `POST /api/audience/apply`: 舵取り指示をプロットへ確定適用
* **受け入れ基準**: `TestClient` で 200 OK が返ること。

---

### Step 10: フロントエンド型定義 (`frontend/src/types/audience.ts`)
* **目標**: TypeScriptインターフェース作成。
* **実装内容**:
  ```typescript
  export interface AudienceSentimentSummary {
    pacing_sentiment: string;
    most_loved_character: string;
    hate_overflow_target: string;
    catharsis_hunger_score: number;
  }
  export interface PlotSteeringDirective {
    action_type: string;
    target_character: string;
    instruction: string;
    affected_episodes: number[];
  }
  ```
* **受け入れ基準**: `npm run typecheck` が通過すること。

---

### Step 11: 読者反応・舵取りパネル (`frontend/src/components/audience/AudienceSteeringPanel.tsx`)
* **目標**: 読者の熱狂や不満を可視化し、プロット変更を承認するUI。
* **実装内容**:
  - ざまぁ渇望度メーター（0〜100%）。
  - 「AIの舵取り提案：第15話のざまぁを第12話へ前倒しします」カード表示。
  - 「プロットへ反映する」ワンクリックボタン。
* **受け入れ基準**: コンポーネントが正常にビルド・表示されること。

---

### Step 12: E2E統合テスト (`tests/e2e/test_audience_steering_pipeline.py`)
* **目標**: コメント受信 → 感情分析 → ディレクティブ生成 → プロット書き換えまでの完結テスト。
* **実装内容**:
  - ヘイト過多コメントを流し込み、次話プロットのイベントが「断罪」に書き換わることをアサート。
* **受け入れ基準**: `pytest tests/e2e/test_audience_steering_pipeline.py` が ALL GREEN。
