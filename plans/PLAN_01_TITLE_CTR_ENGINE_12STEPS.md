# PLAN 01: タイトル＆あらすじCTR爆発エンジン 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 マーケティング・タイトル生成基盤  
**目的**: カクヨムの日間・総合ランキング上位作の構文パターンをメタ解析し、初速CTR（クリック率）を最大化するタイトル・あらすじ生成エンジンを構築する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/marketing_ctr.py` (新規) | タイトル候補・スコアリング・カクヨムメタデータのPydanticモデル定義 |
| **2** | テスト | `tests/unit/marketing/test_trend_syntax.py` (新規) | トレンド構文抽出器の単体テスト作成（TDD先行） |
| **3** | ロジック | `src/services/marketing/trend_syntax_extractor.py` (新規) | タイトル文字列から構文パターン・パワーワードを分解・抽出するロジック |
| **4** | 定義 | `src/config/kakuyomu_syntax_patterns.py` (新規) | カクヨム定番のタイトル構文テンプレート＆NGパターン辞書 |
| **5** | テスト | `tests/unit/marketing/test_ctr_scorer.py` (新規) | CTRスコアリングエンジンの単体テスト作成 |
| **6** | ロジック | `src/services/marketing/ctr_scorer.py` (新規) | 文字数（35〜55字）、感情フック、実利・逆転要素に基づくCTR採点機 |
| **7** | プロンプト | `prompts/templates/marketing/viral_title_generation.j2` (新規) | 30〜50案を同時生成しA/Bテスト候補を絞り込むJinja2プロンプト |
| **8** | プロンプト | `prompts/templates/marketing/viral_synopsis_generation.j2` (新規) | 冒頭3行で読者を掴むあらすじ生成Jinja2プロンプト |
| **9** | エージェント | `src/agents/marketing.py` (修正) | `generate_viral_title_pack()` メソッドの追加統合 |
| **10** | ルーター | `src/backend/routers/marketing_ctr.py` (新規) | タイトル生成＆スコアリング用FastAPIエンドポイント |
| **11** | フロント | `frontend/src/components/marketing/ViralTitleGenerator.tsx` (新規) | タイトル30案一覧・スコアソート・A/Bテスト選択UIコンポーネント |
| **12** | 統合検証 | `tests/e2e/test_title_ctr_pipeline.py` (新規) | 企画入力からタイトル上位3案・あらすじ出力までのE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/marketing_ctr.py`)
* **目標**: タイトル生成およびCTR評価に必要なデータ構造を厳格に定義する。
* **実装内容**:
  ```python
  from pydantic import BaseModel, Field

  class TitleCandidate(BaseModel):
      title: str = Field(..., description="生成されたタイトル文字列")
      char_count: int = Field(..., description="文字数")
      syntax_type: str = Field(..., description="構文パターン名 (追放ざまぁ, 勘違い無双 等)")
      predicted_ctr_score: float = Field(..., ge=0.0, le=100.0, description="CTR予測スコア")
      hooks: list[str] = Field(default_factory=list, description="含まれるフック要素")

  class ViralTitleRequest(BaseModel):
      genre: str = Field(..., description="ジャンル (ファンタジー, 現代ドラマ 等)")
      core_concept: str = Field(..., description="作品の核心設定・独自性")
      protagonist_benefit: str = Field(..., description="主人公の圧倒的強み・実利")
      antagonist_misfortune: str = Field("", description="敵・元仲間へのざまぁ/見下し要素")
      candidate_count: int = Field(30, ge=10, le=50, description="生成候補数")

  class ViralTitleResponse(BaseModel):
      top_recommendations: list[TitleCandidate] = Field(..., min_length=1, max_length=5)
      all_candidates: list[TitleCandidate]
      selected_synopsis: str = Field("", description="連動して生成されたあらすじ")
  ```
* **受け入れ基準**: `mypy src/models/marketing_ctr.py` がエラーゼロで通過すること。

---

### Step 2: トレンド構文抽出テストの作成 (`tests/unit/marketing/test_trend_syntax.py`)
* **目標**: タイトル文字列の分解ロジックを検証するテストを先に用意する。
* **実装内容**:
  ```python
  import pytest
  from src.services.marketing.trend_syntax_extractor import extract_syntax_features

  def test_extract_syntax_features_exile():
      title = "役立たずと追放された付与術師、実は世界唯一の神級エンチャンターでした"
      features = extract_syntax_features(title)
      assert features["syntax_type"] == "追放ざまぁ"
      assert "追放" in features["keywords"]
      assert features["char_count"] == len(title)
      assert features["has_contrast"] is True
  ```
* **受け入れ基準**: `pytest tests/unit/marketing/test_trend_syntax.py` を実行し、モジュール未存在で正しく失敗すること。

---

### Step 3: トレンド構文抽出ロジック (`src/services/marketing/trend_syntax_extractor.py`)
* **目標**: タイトルの構造（前半の理不尽・後半の逆転）を正規表現とキーワードで判定する。
* **実装内容**:
  - `EXILE_PATTERNS = ["追放", "役立たず", "クビ", "追放された", "ゴミ扱い"]`
  - `REVERSAL_PATTERNS = ["実は", "本当は", "覚醒", "世界唯一", "規格外"]`
  - `extract_syntax_features(title: str) -> dict[str, Any]` を実装し、文字数、対比構造の有無、主要フック単語を返す。
* **受け入れ基準**: Step 2 の単体テストが GREEN になること。

---

### Step 4: カクヨム構文定義 (`src/config/kakuyomu_syntax_patterns.py`)
* **目標**: カクヨムでCTRが高い黄金構文テンプレートを定数辞書としてまとめる。
* **実装内容**:
  ```python
  KAKUYOMU_SYNTAX_TEMPLATES = [
      "{disadvantage}と追放された{job}、実は{hidden_power}でした〜{benefit}で{happy_ending}〜",
      "【朗報】{disadvantage}で婚約破棄された私、{reversal}して幸せになりますので邪魔しないでください",
      "{loser_state}から始まる{unique_cheat}無双〜今更戻ってこいと言われてももう遅い〜",
      "Sランクパーティをクビになった{job}、拾われた先は{unexpected_group}でした",
  ]
  CRITICAL_CTR_WORDS = ["実は", "追放", "今更", "無自覚", "規格外", "ざまぁ", "チート", "万能"]
  OPTIMAL_LENGTH_MIN = 35
  OPTIMAL_LENGTH_MAX = 55
  ```
* **受け入れ基準**: 構文テンプレートが最低8種類定義され、プレースホルダーが統一されていること。

---

### Step 5: CTRスコアリング単体テスト (`tests/unit/marketing/test_ctr_scorer.py`)
* **目標**: CTR予測ロジックの動作保証テストを作成。
* **実装内容**:
  - 35〜55文字以内のタイトルが高得点になることの検証。
  - 「追放」と「実は」の対比構造があるタイトルが80点以上になることの検証。
  - 20文字未満または80文字超のタイトルが減点されることの検証。
* **受け入れ基準**: `pytest tests/unit/marketing/test_ctr_scorer.py` が実行可能であること。

---

### Step 6: CTRスコアリングエンジン (`src/services/marketing/ctr_scorer.py`)
* **目標**: タイトル候補を受け取り、カクヨム読者の嗜好に基づく予測スコア（0〜100点）を算出する。
* **実装内容**:
  - 長さスコア（35〜55字なら+30点、範囲外は距離に応じて減点）
  - パワーワードスコア（`CRITICAL_CTR_WORDS` 含有数に応じて最大+30点）
  - 対比・カタルシス構造スコア（理不尽＋大逆転の構造があれば+30点）
  - 記号・可読性スコア（〜、…、カッコ【】の効果的配置で+10点）
* **受け入れ基準**: Step 5 のテストがすべて通過すること。

---

### Step 7: タイトル30案一括生成プロンプト (`prompts/templates/marketing/viral_title_generation.j2`)
* **目標**: LLMに対して、異なる構文パターンで30〜50案のタイトルを一挙に出力させるプロンプトを作成。
* **実装内容**:
  - `{{ core_concept }}`、`{{ protagonist_benefit }}`、`{{ antagonist_misfortune }}` を埋め込む。
  - JSON配列形式 `[{"title": "...", "syntax_type": "..."}]` での厳格出力を強制。
  - 「無難なタイトルは失格」「読者の脳汁が出る煽りを入れよ」というシステム指示を明記。
* **受け入れ基準**: Jinja2レンダリングテストで想定通りのプロンプト文字列が生成されること。

---

### Step 8: あらすじフック生成プロンプト (`prompts/templates/marketing/viral_synopsis_generation.j2`)
* **目標**: タイトルに連動し、カクヨムのあらすじ欄（最初の3行）で読者を落とすプロンプト。
* **実装内容**:
  - 構成: 【1行目：理不尽な状況】【2行目：主人公の圧倒的転機】【3行目：爽快な展開の予告】
  - 余計な世界観の説明（神話、暦、地理）を禁止するネガティブプロンプトを内包。
* **受け入れ基準**: 200〜400文字以内でまとまるあらすじ生成指示になっていること。

---

### Step 9: MarketingAgentへの統合 (`src/agents/marketing.py`)
* **目標**: `MarketingAgent` に `generate_viral_title_pack(request: ViralTitleRequest) -> ViralTitleResponse` を追加。
* **実装内容**:
  - `viral_title_generation.j2` を呼び出し、LLMから30案を取得。
  - 各案に対して `ctr_scorer.score_title()` を実行。
  - スコア降順にソートし、上位3〜5案を `top_recommendations` に格納。
  - 最上位タイトルのためのあらすじを `viral_synopsis_generation.j2` で生成して結合。
* **受け入れ基準**: モックLLMを用いたユニットテストで `ViralTitleResponse` が正しく返ること。

---

### Step 10: FastAPIルーター追加 (`src/backend/routers/marketing_ctr.py`)
* **目標**: フロントエンドから呼び出すAPIエンドポイントを公開する。
* **実装内容**:
  - `POST /api/marketing/viral-titles`
  - 入力: `ViralTitleRequest`
  - 出力: `ViralTitleResponse`
  - `src/backend/main.py` またはルーター一覧へ登録。
* **受け入れ基準**: `TestClient` でリクエストを送り、200 OK と想定JSONが返ること。

---

### Step 11: フロントエンドUI (`frontend/src/components/marketing/ViralTitleGenerator.tsx`)
* **目標**: 作家がジャンルと独自設定を入れると、30案のタイトルがスコア順にカード表示され、ワンクリックで作品タイトルに適用できるUI。
* **実装内容**:
  - スコア80点以上はゴールドバッジ表示。
  - クリックしたタイトルのあらすじプレビュー表示。
  - 「このタイトルを採用」ボタンでメインエディタへ反映。
* **受け入れ基準**: `npm run typecheck`（TypeScript型チェック）が通過すること。

---

### Step 12: E2E統合検証 (`tests/e2e/test_title_ctr_pipeline.py`)
* **目標**: 企画入力からCTRスコアリング、上位タイトル推薦までのパイプラインを一気通貫で検証。
* **実装内容**:
  - 追放系企画リクエストを投入 → 30案生成 → スコアリング → 上位3案が75点以上であることをアサート。
* **受け入れ基準**: `pytest tests/e2e/test_title_ctr_pipeline.py` が ALL GREEN。
