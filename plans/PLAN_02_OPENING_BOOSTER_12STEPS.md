# PLAN 02: 序盤3話特化型 ドーパミン注入・クリフハンガー強制エンジン 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 執筆パイプライン・序盤生成エンジン  
**目的**: カクヨム読者の8割が離脱する「第1話〜第3話」専用の執筆ロジックを分離新設し、開幕0秒インパクトと毎話末尾の強烈なクリフハンガー（引き）を強制する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/opening_booster.py` (新規) | 序盤専用コンテキスト・クリフハンガー採点結果のPydanticモデル定義 |
| **2** | テスト | `tests/unit/writing/test_cliffhanger_scorer.py` (新規) | 話末クリフハンガー判定エンジンの単体テスト作成（TDD先行） |
| **3** | 定義 | `src/config/opening_rules.py` (新規) | 第1話〜第3話の厳格ルール（世界観説明禁止・300字以内事件・プチ快感） |
| **4** | ロジック | `src/services/auditors/cliffhanger_scorer.py` (新規) | エピソード末尾150字の「未解決の危機/衝撃の事実/理不尽」判定機 |
| **5** | テスト | `tests/unit/writing/test_opening_booster.py` (新規) | 序盤特化エージェントの単体テスト作成 |
| **6** | プロンプト | `prompts/templates/narrative/opening_ep01.j2` (新規) | 第1話特化プロンプト（開幕0秒の事件、説明描写の物理的禁止） |
| **7** | プロンプト | `prompts/templates/narrative/opening_ep02.j2` (新規) | 第2話特化プロンプト（逆転の萌芽、主人公の固有スキルの片鱗） |
| **8** | プロンプト | `prompts/templates/narrative/opening_ep03.j2` (新規) | 第3話特化プロンプト（最初のプチざまぁ・周囲の驚嘆・読者引き） |
| **9** | エージェント | `src/agents/writing/opening_booster.py` (新規) | 第1〜3話専用の `OpeningBoosterAgent` 実装 |
| **10** | 結合 | `src/agents/writing/generator.py` (修正) | 話数判定による通常WritingGeneratorとOpeningBoosterの自動ルーティング |
| **11** | 監査連動 | `src/agents/specialists/reader_hook_auditor.py` (修正) | 序盤話数でのクリフハンガー未達時の自動リライト指示発行 |
| **12** | 統合検証 | `tests/e2e/test_opening_booster_pipeline.py` (新規) | 第1話〜第3話の通し生成とクリフハンガー基準達成のE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/opening_booster.py`)
* **目標**: 序盤専用のパラメータとクリフハンガー判定スキーマを定義。
* **実装内容**:
  ```python
  from enum import Enum
  from pydantic import BaseModel, Field

  class CliffhangerType(str, Enum):
      CRISIS = "crisis"              # 命や立場の危機直前で終了
      SHOCKING_TRUTH = "shocking_truth"  # 衝撃の事実判明・裏切りで終了
      TRIUMPH_TRIGGER = "triumph_trigger" # これから反撃という瞬間で終了
      PEACEFUL = "peaceful"          # 平穏（不合格・リライト対象）

  class CliffhangerEvaluation(BaseModel):
      hook_type: CliffhangerType
      score: float = Field(..., ge=0.0, le=100.0)
      reason: str
      tail_sentence: str
      requires_rewrite: bool

  class OpeningEpisodeConfig(BaseModel):
      ep_num: int = Field(..., ge=1, le=3)
      target_word_count: int = Field(2500, ge=1500, le=4000)
      inciting_incident: str
      payoff_moment: str
  ```
* **受け入れ基準**: `mypy src/models/opening_booster.py` が型エラーなく通過すること。

---

### Step 2: クリフハンガー判定テスト作成 (`tests/unit/writing/test_cliffhanger_scorer.py`)
* **目標**: 末尾の文章が「次を読ませる引き」になっているかを正しく採点できるかテストする。
* **実装内容**:
  ```python
  import pytest
  from src.services.auditors.cliffhanger_scorer import score_cliffhanger
  from src.models.opening_booster import CliffhangerType

  def test_score_cliffhanger_crisis():
      text = "…その時、背後の扉が轟音と共に蹴り破られた。「見つけたぞ、裏切り者め」"
      result = score_cliffhanger(text)
      assert result.hook_type == CliffhangerType.CRISIS
      assert result.score >= 80.0
      assert result.requires_rewrite is False

  def test_score_cliffhanger_peaceful_fails():
      text = "今日も良い一日だった。主人公は温かいベッドに入り、静かに眠りについた。"
      result = score_cliffhanger(text)
      assert result.hook_type == CliffhangerType.PEACEFUL
      assert result.score < 50.0
      assert result.requires_rewrite is True
  ```
* **受け入れ基準**: `pytest` 実行でモジュール未実装による失敗が確認できること。

---

### Step 3: 序盤執筆ルール定義 (`src/config/opening_rules.py`)
* **目標**: 第1話〜第3話で厳守すべき創作制約をテキスト定数化する。
* **実装内容**:
  ```python
  OPENING_FORBIDDEN_RULES = [
      "【世界観の解説禁止】歴史、魔法体系、神話、暦、地理の客観的説明は1行たりとも書くな。",
      "【主人公の平凡自称禁止】『俺はどこにでもいる平凡な〜』という陳腐な導入を禁ずる。",
      "【のんびりした日常禁止】冒頭300字以内に必ず『理不尽な通告・襲撃・絶縁』を起こせ。",
      "【平穏な終わり方の禁止】各話の最後は必ず『新たな敵の出現』か『主人公の凶暴な笑み』で切れ。",
  ]
  OPENING_EPISODE_TARGETS = {
      1: "理不尽な追放・虐げの提示 → どん底の中で手に入れた未知の力/転機 → 絶叫または冷笑で引く",
      2: "旧勢力の手の届かない場所への到達 → チート能力の初発現 → 驚くヒロイン/観察者で引く",
      3: "追放者側の困窮の描写（ざまぁの萌芽） → 主人公の圧倒的活躍 → 評価の急上昇で引く",
  }
  ```
* **受け入れ基準**: 定数辞書が過不足なく定義されていること。

---

### Step 4: クリフハンガー採点エンジン (`src/services/auditors/cliffhanger_scorer.py`)
* **目標**: 本文末尾の150文字を解析し、読者が「次のページ」を押さずにいられないか判定する。
* **実装内容**:
  - `score_cliffhanger(tail_text: str) -> CliffhangerEvaluation`
  - キーワード検知（足音、扉、突然、現れた、笑った、告げた、血、爆音 等で加点）
  - 平穏キーワード検知（眠りについた、朝を迎えた、安堵した、静かになった 等で大幅減点）
  - 60点未満は `requires_rewrite = True` を設定。
* **受け入れ基準**: Step 2 のテストが ALL GREEN になること。

---

### Step 5: 序盤特化エージェント単体テスト (`tests/unit/writing/test_opening_booster.py`)
* **目標**: `OpeningBoosterAgent` のプロンプト生成と生成結果の検証テストを用意する。
* **実装内容**:
  - 第1話用プロンプトに `OPENING_FORBIDDEN_RULES` が正しく埋め込まれているか検証。
  - 第1話〜第3話でそれぞれ異なるターゲット指示が反映されるか検証。
* **受け入れ基準**: テストファイルが作成され、実行可能な状態であること。

---

### Step 6: 第1話特化プロンプト (`prompts/templates/narrative/opening_ep01.j2`)
* **目標**: 第1話に特化した高密度Jinja2テンプレートを作成。
* **実装内容**:
  - 指示: 「冒頭の第1文目は、主人公が直面している物理的危機または決定的な侮蔑の台詞から開始せよ」
  - 構成指示: 【発端：侮辱と追放 (30%)】→【孤立と絶望 (30%)】→【異変と未知の力の発現 (30%)】→【クリフハンガー (10%)】
  - 禁止事項: 過去回想を3行以上続けることの禁止。
* **受け入れ基準**: テンプレートが構文エラーなくレンダリングできること。

---

### Step 7: 第2話特化プロンプト (`prompts/templates/narrative/opening_ep02.j2`)
* **目標**: 第2話（新天地・チートの実感）特化テンプレートを作成。
* **実装内容**:
  - 指示: 「手に入れた能力の異常性を、主人公以外の第三者（モンスター、美少女、通りすがりの冒険者）の視線や反応を通して描写せよ」
  - 末尾指示: 「新たな味方との出会い、または元仲間たちの後悔の兆候を提示して切れ」
* **受け入れ基準**: テンプレートが正しくレンダリングできること。

---

### Step 8: 第3話特化プロンプト (`prompts/templates/narrative/opening_ep03.j2`)
* **目標**: 第3話（初速の快感・★獲得誘導）特化テンプレートを作成。
* **実装内容**:
  - 指示: 「読者が『ザマァみろ！』と快哉を叫ぶ、最初のスカッと展開を描け」
  - 末尾指示: 「読者に『この先どうなるんだ！？』と期待させ、カクヨムのフォローと★を自然に入れたくなるような圧倒的スケールの謎や強敵を提示して切れ」
* **受け入れ基準**: テンプレートが正しくレンダリングできること。

---

### Step 9: `OpeningBoosterAgent` 実装 (`src/agents/writing/opening_booster.py`)
* **目標**: 第1話〜第3話専用の独立エージェントクラスを実装。
* **実装内容**:
  ```python
  from src.agents.base import BaseAgent
  from src.services.auditors.cliffhanger_scorer import score_cliffhanger

  class OpeningBoosterAgent(BaseAgent):
      async def generate_opening_episode(self, book_id: int, ep_num: int, context: dict) -> str:
          # ep_num (1, 2, 3) に応じた特化テンプレートを選択して執筆
          # 生成後、末尾150文字を score_cliffhanger で即座に監査
          # スコア < 60 の場合は末尾部分のみ最大2回自動再生成
          pass
  ```
* **受け入れ基準**: Step 5 の単体テストが通過すること。

---

### Step 10: WritingGeneratorへのルーティング組み込み (`src/agents/writing/generator.py`)
* **目標**: エピソード生成パイプラインで話数が 1〜3 の場合に `OpeningBoosterAgent` へ自動委譲する。
* **実装内容**:
  - `generate_episodes_pipeline` 内で `if ep_num in (1, 2, 3): return await self.opening_booster.generate(...)` の分岐を追加。
  - 第4話以降は既存の長編用パイプラインをそのまま維持。
* **受け入れ基準**: 既存の `WritingGenerator` テストを壊さず、新ルーティングが機能すること。

---

### Step 11: ReaderHookAuditor連携 (`src/agents/specialists/reader_hook_auditor.py`)
* **目標**: 監査専門エージェントが、第1〜3話に対してより厳しい閾値（80点以上）を適用するよう改修。
* **実装内容**:
  - `ReaderHookAuditor.audit()` 内で、`ctx.get("ep_num") <= 3` の場合にクリフハンガー評価を合否判定に組み込む。
* **受け入れ基準**: 序盤話数でフックが弱い場合に `ReaderHookAuditor` がリライトディレクティブを発行すること。

---

### Step 12: 統合E2Eテスト (`tests/e2e/test_opening_booster_pipeline.py`)
* **目標**: 第1話〜第3話を連続生成し、すべての話末がクリフハンガー合格基準を満たすことを検証。
* **実装内容**:
  - テスト用設定で1〜3話を生成 → 各話末尾の `CliffhangerType` が `PEACEFUL` ではないことを検証。
* **受け入れ基準**: `pytest tests/e2e/test_opening_booster_pipeline.py` が ALL GREEN。
