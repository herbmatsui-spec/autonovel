# PLAN 16: キャラクターボイス辞書・会話文自動正規化＆トーン保護 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 キャラクター管理、会話文生成・検証パイプライン (`src/models/character.py`, `src/agents/writing/`)  
**目的**: 長編連載（10〜30話以降）において、脇役や敵役の口調が主人公や地の文に同化・漂白（標準語化・丁寧語化）してしまうAI特有の「キャラ崩壊」を根本的に防ぐ。キャラクターごとに一人称・二人称・特有語尾・口癖・禁止語を厳格に定義し、生成されたセリフを自動検証・自動修復する専用リンターを構築する。  
**前提**: 地の文は修正せず、カギ括弧（`「」`）内の発話者特定とセリフ語尾のみを精密に正規化する。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/character_voice_profile.py` (新規) | 一人称・二人称・語尾パターン・口癖・禁止語のPydanticモデル定義 |
| **2** | 辞書拡張 | `src/backend/database/models.py` (修正) | `Character` テーブルに `voice_profile_json` カラムを追加 |
| **3** | セリフ抽出 | `src/services/character/dialogue_extractor.py` (新規) | 小説本文からカギ括弧セリフと直前のト書きから話者を高精度特定するパーサー |
| **4** | リンター | `src/services/character/voice_linter.py` (新規) | 抽出したセリフがキャラのボイスプロファイルに合致しているか判定するルールエンジン |
| **5** | 修復プロンプト | `prompts/templates/narrative/dialogue_repair.j2` (新規) | キャラ崩壊したセリフを本来の口調・トーンへ外科的に差し替えるプロンプト |
| **6** | 自動修復機 | `src/services/character/voice_normalizer.py` (新規) | 不一致セリフをルール置換（辞書ベース）または軽量LLMで自動修復するサービス |
| **7** | プリセット集 | `src/data/voice_archetypes.json` (新規) | 王道ツンデレ、のじゃロリ、粗暴俺様、忠臣従者等の定番ボイスプロファイル集 |
| **8** | プロンプト強化 | `prompts/manager.py` (修正) | 執筆プロンプトへの `【絶対口調制約】` の自動インジェクション強化 |
| **9** | 執筆統合 | `src/agents/writing/episode_writer.py` (修正) | 本文生成後に `VoiceNormalizer` を自動通過させる後処理パイプライン統合 |
| **10** | フロントUI | `frontend/src/components/character/VoiceProfileEditor.tsx` (新規) | 口調プリセット選択、一人称・語尾・サンプルセリフ入力UIコンポーネント |
| **11** | キャラ診断UI | `frontend/src/components/editor/CharacterConsistencyBadge.tsx` (新規) | エディタ上でキャラの口調一致度（100%一致、語尾揺れ検知）を表示するバッジ |
| **12** | 統合検証 | `tests/unit/test_character_voice_linter.py` (新規) | 話者誤認、一人称ブレ（私/僕/俺）、語尾ブレの検知・自動修復を検証する単体テスト |

---

## 各ステップの詳細仕様

### Step 1: ボイスプロファイルPydanticモデル定義 (`src/models/character_voice_profile.py`)
* **目標**: キャラクターの発話ルールを機械可読な構造として定義。
* **実装内容**:
  ```python
  from __future__ import annotations
  from pydantic import BaseModel, Field

  class CharacterVoiceProfile(BaseModel):
      character_name: str
      first_person: list[str] = Field(..., description="一人称 (例: ['俺', 'オレ'])")
      second_person: list[str] = Field(..., description="二人称 (例: ['お前', '貴様'])")
      endings: list[str] = Field(..., description="許可される語尾 (例: ['〜だぜ', '〜な'])")
      forbidden_words: list[str] = Field(default_factory=list, description="絶対に使わない語彙")
      catchphrases: list[str] = Field(default_factory=list, description="口癖・決め台詞")
      sample_dialogue: str = Field("", description="代表的なセリフ例")
  ```
* **受け入れ基準**: `mypy src/models/character_voice_profile.py` でエラーゼロ。

---

### Step 2: ORMモデルへのカラム追加 (`src/backend/database/models.py`)
* **目標**: キャラクター定義にボイスプロファイルJSONを永続化。
* **実装内容**:
  - `Character` テーブルに `voice_profile_json = Column(JSON, nullable=True)` を追加。
* **受け入れ基準**: マイグレーション後にボイスプロファイルの保存・読み込みができること。

---

### Step 3: セリフ・話者特定パーサー (`src/services/character/dialogue_extractor.py`)
* **目標**: 本文中の各セリフ（`「……」`）が「誰の発話か」を直前直後のト書きから推定。
* **実装内容**:
  - `「……」と、アリスは言った。` → 話者: アリス
  - 2人の交互会話におけるターン推定（ヒューリスティクス）。
* **受け入れ基準**: 典型的なラノベ形式の会話文で話者正解率90%以上を達成すること。

---

### Step 4: ボイスリンター実装 (`src/services/character/voice_linter.py`)
* **目標**: セリフ内の口調ルール違反を検知。
* **実装内容**:
  - 一人称チェック: 俺設定のキャラが「僕」「私」と喋っていないか。
  - 二人称チェック: 貴様設定のキャラが「あなた」と呼んでいないか。
  - 語尾チェック: 正規表現で文末が `endings` に合致するかを判定。
* **受け入れ基準**: 意図的に混入させた一人称・語尾エラーを100%検出できること。

---

### Step 5: セリフ修復Jinja2プロンプト (`prompts/templates/narrative/dialogue_repair.j2`)
* **目標**: 単純置換では不自然になる複雑なセリフを、キャラの口調を維持して再表現。
* **実装内容**:
  - 発話内容のニュアンスを変えず、語尾と一人称のみをボイスプロファイルに厳格適応。
* **受け入れ基準**: 文意を損なわずに口調のみが変換されるプロンプト。

---

### Step 6: 自動修復サービス (`src/services/character/voice_normalizer.py`)
* **目標**: リンターで検出されたエラーを自動的に修正。
* **実装内容**:
  - 一人称の単純置換（「僕」→「俺」）は辞書ベースで即時置換（高速）。
  - 語尾の不一致は軽量プロンプトまたはルール変換器で修正。
* **受け入れ基準**: 修正後のテキストがリンターを完全にパスすること。

---

### Step 7: ボイスアーキタイプ辞書 (`src/data/voice_archetypes.json`)
* **目標**: ユーザーがワンクリックで選べる定番キャラクター口調集。
* **実装内容**:
  - `tsundere`: 「べ、別に」「〜じゃない！」「あんた」
  - `ojousama`: 「〜ですわ」「〜ましてよ」「わたくし」
  - `cool_soldier`: 「了解した」「〜だ」「貴公」
  - `boy_hero`: 「〜だよな」「〜っしょ」「僕」
* **受け入れ基準**: 10種類以上の定番アーキタイプが定義されていること。

---

### Step 8: 執筆プロンプトへの制約注入 (`prompts/manager.py`)
* **目標**: 執筆エージェントが最初からキャラの口調を守るよう事前ガード。
* **実装内容**:
  - 各キャラの `first_person` と `endings` をプロンプトの `【ダイアログ・プロファイル】` に動的展開。
* **受け入れ基準**: 執筆プロンプトにキャラクターごとの厳格なセリフ制約が出力されること。

---

### Step 9: 執筆パイプラインへの統合 (`src/agents/writing/episode_writer.py`)
* **目標**: 本文生成の直後にボイスノーマライザーを自動適用。
* **実装内容**:
  - 生成された本文に対して `VoiceNormalizer.normalize(content, book_id)` を実行。
* **受け入れ基準**: エピソード生成パイプラインを通じて、キャラ崩壊のない文章が出力されること。

---

### Step 10: フロントエンド ボイスプロファイル編集UI (`frontend/src/components/character/VoiceProfileEditor.tsx`)
* **目標**: キャラクター作成画面で口調を直感的に設定できるUI。
* **実装内容**:
  - プリセット選択ボタン（「お嬢様」「俺様」「従者」）。
  - 一人称・二人称・語尾のタグ入力欄。
  - セリフプレビュー。
* **受け入れ基準**: 選択したプリセットが入力欄に即時反映され、保存できること。

---

### Step 11: キャラ整合性診断バッジ (`frontend/src/components/editor/CharacterConsistencyBadge.tsx`)
* **目標**: 作家がエディタ上でキャラクターの一貫性を視覚的に確認。
* **実装内容**:
  - エディタ上部に `[🗣️ キャラ口調一致度: 98% (アリスの語尾に1件揺れあり)]` を表示。
  - クリックで該当セリフへジャンプ。
* **受け入れ基準**: 語尾揺れがあるセリフがハイライトされること。

---

### Step 12: キャラクターボイス単体テスト (`tests/unit/test_character_voice_linter.py`)
* **目標**: リンターとノーマライザーの動作をテストコードで検証。
* **実装内容**:
  - 「俺様」設定のキャラが「わたしは嬉しいです」と喋った場合、「俺は嬉しいぜ」等に正しく修復されることをアサート。
* **受け入れ基準**: `pytest tests/unit/test_character_voice_linter.py` が PASS すること。
