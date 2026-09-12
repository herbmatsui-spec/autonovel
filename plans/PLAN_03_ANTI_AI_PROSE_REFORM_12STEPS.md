# PLAN 03: AI優等生病の外科的切除 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 Anti-AI監査・文体生成エンジン  
**目的**: LLM特有の「感情の三段論法（説明的内省・優等生的まとめ）」を検知・排除し、読者の本音を代弁する「生々しいエゴ・下品な打算・偏執的な毒気」を文章に宿す。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/character_flaw.py` (新規) | キャラクターの俗物的動機・毒（Flaw & Fetish）スキーマ定義 |
| **2** | テスト | `tests/unit/anti_ai/test_syllogism_detector.py` (新規) | 感情の三段論法検知器の単体テスト作成（TDD先行） |
| **3** | パターン | `src/services/anti_ai/syllogism_patterns.py` (新規) | 「〜と感じた。なぜなら〜」「〜と自分を納得させた」等のAI説明構文辞書 |
| **4** | 検知器 | `src/services/anti_ai/detectors.py` (修正) | `EmotionSyllogismDetector` を実装し既存検知器リストへ追加 |
| **5** | 定義 | `src/config/flaw_and_fetish.py` (新規) | 打算・復讐心・異常な独占欲・見下し快感のプリセット集 |
| **6** | プロンプト | `prompts/templates/narrative/raw_emotion_instruction.j2` (新規) | 生理的反応（舌打ち、冷笑、胃痛）への置換を命じるJinja2プロンプト |
| **7** | テスト | `tests/unit/writing/test_flaw_injection.py` (新規) | コンテキストビルダーへの毒要素注入テスト |
| **8** | 統合 | `src/agents/context_builder_agent.py` (修正) | 登場人物コンテキストに俗物動機・裏の顔（Flaw）を自動付与 |
| **9** | 執筆連携 | `src/agents/prompt_composer.py` (修正) | 本文執筆プロンプトに `raw_emotion_instruction` を自動挿入 |
| **10** | 監査更新 | `src/services/anti_ai/orchestrator.py` (修正) | 三段論法スコアを総合AIペナルティ計算式に統合 |
| **11** | リライト | `src/services/anti_ai/rewrite_directive_generator.py` (新規) | 三段論法検知時に「身体言語・生々しい呟きへの置換」指示を生成 |
| **12** | 統合検証 | `tests/e2e/test_anti_ai_emotion_reform.py` (新規) | 優等生的文章が排除され、エゴと毒が効いた文章が出力されるE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/character_flaw.py`)
* **目標**: キャラクターの「建前」と「本音（毒）」を管理するデータ構造を定義。
* **実装内容**:
  ```python
  from pydantic import BaseModel, Field

  class SecretMotive(BaseModel):
      motive_type: str = Field(..., description="打算の種類 (金銭欲, 承認欲求, 独占欲, 復讐心 等)")
      inner_monologue_sample: str = Field(..., description="心の中のゲスな呟きの例")
      physical_trigger: str = Field(..., description="感情が高ぶった際に出る身体的癖 (舌打ち, 爪を噛む 等)")

  class CharacterFlawProfile(BaseModel):
      character_name: str
      surface_persona: str = Field(..., description="表向きの善良な態度")
      secret_flaw: SecretMotive = Field(..., description="裏の俗物的な動機")
      target_of_contempt: str = Field("", description="内心見下している対象")
  ```
* **受け入れ基準**: `mypy src/models/character_flaw.py` がエラーなく通ること。

---

### Step 2: 三段論法検知テスト作成 (`tests/unit/anti_ai/test_syllogism_detector.py`)
* **目標**: AI特有の「感情の説明・自己説得」構文を検出するテストを用意する。
* **実装内容**:
  ```python
  import pytest
  from src.services.anti_ai.detectors import EmotionSyllogismDetector

  def test_detect_syllogism_pattern():
      detector = EmotionSyllogismDetector()
      text = "彼は怒りを感じた。なぜなら大切な仲間を侮辱されたからだ。しかし、今は耐えるべきだと自分に言い聞かせた。"
      violations = detector.detect(text)
      assert len(violations) >= 1
      assert "なぜなら" in violations[0].text or "言い聞かせた" in violations[0].text
  ```
* **受け入れ基準**: テスト実行でモジュール未定義エラーが正しく返ること。

---

### Step 3: 三段論法パターン定義 (`src/services/anti_ai/syllogism_patterns.py`)
* **目標**: LLMが書く「説明的な感情処理」の正規表現パターンを網羅する。
* **実装内容**:
  ```python
  import re

  SYLLOGISM_PATTERNS = [
      re.compile(r"(?:怒り|悲しみ|恐怖|歓喜|戸惑い)を(?:感じた|覚えた)。(?:なぜなら|というのも)"),
      re.compile(r"(?:べきだと|なければならないと)(?:自分に言い聞かせた|心に誓った)"),
      re.compile(r"一瞬(?:躊躇|迷っ)たが、(?:気を取り直して|思い直して|意を決して)"),
      re.compile(r"理不尽だと(?:思いつつ|感じながら)も、(?:大人の対応|冷静さを保)"),
  ]
  ```
* **受け入れ基準**: 最低4種類の典型的AI構文パターンがコンパイル済み正規表現として定義されていること。

---

### Step 4: 三段論法検出器の実装 (`src/services/anti_ai/detectors.py`)
* **目標**: `BaseRuleDetector` を継承した `EmotionSyllogismDetector` を実装する。
* **実装内容**:
  - `AICategory.EMOTION_SYLLOGISM` を新設。
  - テキスト内のパターンマッチ箇所を `ViolationSpan` として収集。
  - 1エピソードあたり2箇所以上でスコア減点。
* **受け入れ基準**: Step 2 のテストが GREEN になること。

---

### Step 5: 毒と打算のプリセット辞書 (`src/config/flaw_and_fetish.py`)
* **目標**: カクヨム読者を惹きつける「俗物的な本音」のサンプル定義。
* **実装内容**:
  ```python
  FLAW_PRESETS = {
      "calculating_merchant": {
          "motive_type": "絶対的損得勘定",
          "inner_monologue_sample": "人助けなんて一文の得にもならねえ。だが、恩を売っておけば後で10倍搾り取れる。",
          "physical_trigger": "懐の金貨の重みを指先で確かめる",
      },
      "twisted_inferiority": {
          "motive_type": "見下し快感",
          "inner_monologue_sample": "かつて俺を虫ケラ扱いした連中が、今や俺の靴を舐めたがっている。傑作だな。",
          "physical_trigger": "口の端を吊り上げて静かに息を吐く",
      },
  }
  ```
* **受け入れ基準**: 最低5系統の俗物プリセットが辞書として登録されていること。

---

### Step 6: 生々しいエゴ注入プロンプト (`prompts/templates/narrative/raw_emotion_instruction.j2`)
* **目標**: 本文執筆時に「優等生的な内省」を物理的に封じるプロンプト。
* **実装内容**:
  - 指示: 「キャラクターの道徳的な正しさを捨てよ。善行を行う際も、心の中では徹底的に下品な打算や相手への見下しを抱かせよ」
  - 指示: 「感情を理由と共に説明するな。『舌打ち』『冷たい笑み』『胃の奥の疼き』などの生理現象のみで語れ」
* **受け入れ基準**: テンプレートが正しくレンダリングできること。

---

### Step 7: 毒要素注入単体テスト (`tests/unit/writing/test_flaw_injection.py`)
* **目標**: キャラクター情報に `secret_flaw` が自動付与されることを検証するテスト。
* **実装内容**:
  - 主人公データに Flaw が設定されていない場合、プリセットから自動補完されることを検証。
* **受け入れ基準**: テストが正しく実行できること。

---

### Step 8: ContextBuilderAgent拡張 (`src/agents/context_builder_agent.py`)
* **目標**: キャラクターの動的コンテキスト構築時に `CharacterFlawProfile` を結合する。
* **実装内容**:
  - `build_character_context` 内で、各登場人物の「表の顔」と「裏の打算（Flaw）」を明確に対比してプロンプト変数へ格納。
* **受け入れ基準**: 既存のコンテキスト構築を壊さずに新フィールドが追加されること。

---

### Step 9: PromptComposer執筆プロンプト統合 (`src/agents/prompt_composer.py`)
* **目標**: 最終執筆プロンプト（`final_writing_prompt.j2`）の冒頭に `raw_emotion_instruction.j2` を埋め込む。
* **実装内容**:
  - `compose_writing_prompt()` 内で、`density_level` やキャラクターの Flaw 情報に応じて感情制約を追加注入。
* **受け入れ基準**: 生成されたプロンプト文字列に生々しい感情指示が含まれていること。

---

### Step 10: AntiAIDetectorオーケストレーター統合 (`src/services/anti_ai/orchestrator.py`)
* **目標**: `RuleBasedAntiAIDetector` が三段論法検出器を自動実行するように登録。
* **実装内容**:
  - `RULE_DETECTORS` 辞書に `AICategory.EMOTION_SYLLOGISM: EmotionSyllogismDetector` を追加。
  - 重み付け（`DEFAULT_CATEGORY_WEIGHTS`）に新カテゴリーを追加。
* **受け入れ基準**: `detector.detect()` で三段論法違反が総合スコアに正しく反映されること。

---

### Step 11: リライト指示生成器 (`src/services/anti_ai/rewrite_directive_generator.py`)
* **目標**: 三段論法が検知された場合、PDCAリライトループで具体的な修正指示を出す。
* **実装内容**:
  - 「【修正指示】「〜と感じた。なぜなら〜」という優等生的な内省を削除し、キャラクターの「舌打ち」または「心の中での下品な独白」に置き換えてください。」
* **受け入れ基準**: 違反箇所を含むテキストから適切な Actionable Diff 指示が生成されること。

---

### Step 12: E2E統合検証 (`tests/e2e/test_anti_ai_emotion_reform.py`)
* **目標**: 本文生成 → Anti-AI監査 → 必要に応じたリライトの一連の流れを検証。
* **実装内容**:
  - 生成された文章の `EmotionSyllogismDetector` 違反数がゼロであること、かつキャラクターの打算独白が含まれることを検証。
* **受け入れ基準**: `pytest tests/e2e/test_anti_ai_emotion_reform.py` が ALL GREEN。
