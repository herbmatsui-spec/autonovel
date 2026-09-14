# PLAN 14: スマート校正LLM＆商業ラノベFew-Shot動的注入 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 本文生成・文体推敲パイプライン、フォーマッター層  
**目的**: 正規表現による安易な文字置換（文法崩壊や「言うまでもないが」の誤削除）を廃止し、安価・超高速な軽量LLM（Gemini 2.0 Flash / GPT-4o-mini）を用いた文脈保持型スマート校正エージェントを導入する。また、プロ作家レベルの商業ライトノベルFew-Shotをジャンル別に動的注入し、「AI臭さ」を根本から払拭する。  
**前提**: 執筆エージェントの出力後、1秒未満・極小トークンコストで推敲を完了する軽量パイプライン。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/prose_refinement.py` (新規) | 推敲指示、校正前後差分、Few-ShotメタデータのPydanticモデル定義 |
| **2** | サンプル集 | `src/data/genre_few_shots.json` (新規) | 商業ラノベ水準の高品質描写サンプル（情景、感情、戦闘、日常）のジャンル別辞書 |
| **3** | セレクター | `src/services/prose/few_shot_selector.py` (新規) | ジャンル・シーンタイプ（戦闘/会話/心理）に応じて最適なFew-Shotを動的選択するロジック |
| **4** | プロンプト | `prompts/templates/narrative/smart_prose_refine.j2` (新規) | AI紋切り型（息を呑む、特筆すべき等）を文脈を壊さずに五感描写へ昇華させるプロンプト |
| **5** | エージェント | `src/agents/writing/prose_refiner_agent.py` (新規) | 軽量LLM（Gemini Flash）を呼び出し、1パスで文法保持推敲を行うエージェント |
| **6** | 置換コード整理 | `formatters/kakuyomu.py` (修正) | 破壊的な正規表現置換（`remove_ai_isms`）を削除し、禁則処理・インデント整形に特化 |
| **7** | パイプライン統合 | `src/agents/writing/episode_writer.py` (修正) | 初稿生成直後に `ProseRefinerAgent` を自動通過させる統合処理 |
| **8** | キャッシュ | `src/services/prose/refinement_cache.py` (新規) | 同一表現の不要な再推敲を防ぐLRUインメモリキャッシュ |
| **9** | 設定トグル | `src/backend/config.py` (修正) | スマート推敲の有効/無効、推敲強度（Mild / Balanced / Literary）の設定追加 |
| **10** | フロントUI | `frontend/src/components/style/ProsePolishSettings.tsx` (新規) | ユーザーが推敲レベル（標準/文学的/軽快）を選択できるUIコントロール |
| **11** | 差分可視化 | `frontend/src/components/editor/ProseRefineDiffModal.tsx` (新規) | AI特有表現がどのように自然な日本語描写に推敲されたかを確認できる差分モーダル |
| **12** | 統合検証 | `tests/unit/test_smart_prose_refiner.py` (新規) | 文法破綻（接続詞抜け等）が生じず、AI-ismsが自然に置換されることを検証するテスト |

---

## 各ステップの詳細仕様

### Step 1: 推敲データ構造モデル (`src/models/prose_refinement.py`)
* **目標**: 推敲前後のテキスト、改善されたAI-ismsのメタデータを管理。
* **実装内容**:
  ```python
  from __future__ import annotations
  from pydantic import BaseModel, Field

  class RefinementDetail(BaseModel):
      original_phrase: str
      refined_phrase: str
      reason: str  # 例: "感情説明から身体反応描写へ変更"

  class ProseRefineResult(BaseModel):
      refined_text: str
      modifications: list[RefinementDetail] = Field(default_factory=list)
      total_fixes_count: int = 0
      latency_ms: float = 0.0
  ```
* **受け入れ基準**: `mypy src/models/prose_refinement.py` でエラーゼロ。

---

### Step 2: 商業ラノベFew-Shot辞書 (`src/data/genre_few_shots.json`)
* **目標**: AI小説の陳腐な構文を打破するプロ作家級の描写サンプルを集約。
* **実装内容**:
  - `fantasy_action`: 剣戟の速度、風圧、金属音、皮膚に伝わる殺気の描写例。
  - `villainess_court`: 扇子の開き方、視線の冷たさ、貴族の皮肉、衣擦れの音。
  - `dungeon_modern`: アスファルトの照り返し、モンスターの悪臭、心拍数の上昇。
* **受け入れ基準**: 各ジャンルに最低3つの高品質なBefore/Afterペアが定義されていること。

---

### Step 3: Few-Shot動的セレクター (`src/services/prose/few_shot_selector.py`)
* **目標**: プロンプトのトークン上限を圧迫せず、必要な1〜2例のみを動的に選択。
* **実装内容**:
  - シーンの属性（`action`, `dialogue`, `internal_monologue`）を判定。
  - 最も関連度の高いサンプルのみをプロンプトコンテキストへ注入。
* **受け入れ基準**: 与えられたジャンル・シーンに合致するFew-Shot文字列が高速返却されること。

---

### Step 4: スマート推敲Jinja2プロンプト (`prompts/templates/narrative/smart_prose_refine.j2`)
* **目標**: 文意とストーリー進行を100%維持したまま、文体のみをプロ水準に研磨。
* **実装内容**:
  - 指示内容:
    1. 「〜と感じた」「息を呑んだ」「静寂が支配した」等の定型句を、五感と具体的な身体の動きに直せ。
    2. 主語・述語の係り受け、接続詞を絶対に壊すな。
    3. 会話文のセリフそのものは改変せず、ト書き（地の文）のテンポを整えよ。
* **受け入れ基準**: プロンプトレンダリングが正常に行われること。

---

### Step 5: スマート推敲エージェント (`src/agents/writing/prose_refiner_agent.py`)
* **目標**: Gemini 2.0 Flash / GPT-4o-mini による高速推敲（0.8秒以内）。
* **実装内容**:
  ```python
  class ProseRefinerAgent(BaseAgent):
      async def refine(self, draft_text: str, genre: str, style_intensity: str = "balanced") -> ProseRefineResult:
          # Few-shot選択 & プロンプト構築
          # 超軽量モデル呼び出し
          # 出力テキストと修正箇所のパース
          ...
  ```
* **受け入れ基準**: 3,000文字のテキストを高速かつ低コストに推敲できること。

---

### Step 6: カクヨムフォーマッターの正規表現除去 (`formatters/kakuyomu.py`)
* **目標**: 危険な正規表現置換コードの削除。
* **実装内容**:
  - `remove_ai_isms` 関数内の粗雑な置換ルール（`re.sub(r"言うまでもない[がか]?、?", "", text)` 等）を削除。
  - 代わりに、行頭全角スペース付与、三段落の空行調整、約物（`――`、`……`）の禁則処理のみに専念。
* **受け入れ基準**: 元の文章の文法を壊すことなく、純粋なフォーマット整形のみが行われること。

---

### Step 7: 執筆パイプラインへの推敲エージェント統合 (`src/agents/writing/episode_writer.py`)
* **目標**: 執筆完了時に自動的に推敲プロセスをトリガー。
* **実装内容**:
  - `EpisodeWriter.write(...)` の末尾で `ProseRefinerAgent.refine(...)` を呼び出す。
  - 設定で無効化されている場合はスキップするフォールバック機構。
* **受け入れ基準**: エピソード生成パイプライン実行時に、推敲済みテキストが返却されること。

---

### Step 8: LRU推敲キャッシュ (`src/services/prose/refinement_cache.py`)
* **目標**: 定型的なフレーズや段落の推敲結果をキャッシュしてAPIコストを削減。
* **実装内容**:
  - ハッシュキー（テキスト＋ジャンル）によるメモリキャッシュ。
* **受け入れ基準**: 同一テキスト入力時にLLMを呼ばずにキャッシュヒットすること。

---

### Step 9: アプリケーション設定への推敲パラメータ追加 (`src/backend/config.py`)
* **目標**: 環境変数および設定画面からの制御を可能にする。
* **実装内容**:
  - `PROSE_REFINER_ENABLED: bool = True`
  - `PROSE_REFINER_MODEL: str = "gemini-2.0-flash"`
  - `PROSE_REFINER_STYLE: str = "balanced"`
* **受け入れ基準**: 設定の読み込みと動的オーバーライドが機能すること。

---

### Step 10: フロントエンド推敲設定UI (`frontend/src/components/style/ProsePolishSettings.tsx`)
* **目標**: ユーザーが好みの文体研磨レベルを選択可能にする。
* **実装内容**:
  - セレクトボックス: `[自然・軽快 (Web標準)] [重厚・文学的 (ラノベ大賞風)] [原文重視 (高速)]`
* **受け入れ基準**: UI上の選択がバックエンドのAPIパラメータに反映されること。

---

### Step 11: 推敲前後差分確認モーダル (`frontend/src/components/editor/ProseRefineDiffModal.tsx`)
* **目標**: どこがどう良くなったかを視覚的に確認できる機能。
* **実装内容**:
  - 左: 生成原文、右: 推敲後。修正された表現をハイライト表示。
* **受け入れ基準**: ユーザーが推敲の価値を実感できる美しい差分プレビューが表示されること。

---

### Step 12: スマート推敲単体テスト (`tests/unit/test_smart_prose_refiner.py`)
* **目標**: 文法崩壊（主語欠落等）が起きないことをテスト。
* **実装内容**:
  - 「言うまでもないが、彼は天才だった」が「言うまでもなく、彼の才能は群を抜いていた」等に自然に変換され、「、彼は天才だった」といった文法エラーにならないことを検証。
* **受け入れ基準**: `pytest tests/unit/test_smart_prose_refiner.py` が PASS すること。
