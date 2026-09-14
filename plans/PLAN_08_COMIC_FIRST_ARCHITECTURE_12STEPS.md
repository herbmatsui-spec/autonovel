# PLAN 08: コミカライズ逆算設計（Comic-First Architecture） 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 本文執筆・メディアミックス連動基盤  
**目的**: 出版社の編集者がカクヨム作品を書籍化・コミカライズ（Webtoon含む）する最大の決定打である「マンガにしたときにバズる決定的な見開き・キラーカット（表情差分・視覚的落差）」を先に設計し、その絵面に向けて小説本文を逆算生成する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/comic_first.py` (新規) | キラーカット（決めゴマ）、視覚落差、コマ割り設計のPydanticモデル定義 |
| **2** | テスト | `tests/unit/media/test_killer_cut_planner.py` (新規) | 各話のキラーカット自動選定ロジックの単体テスト作成（TDD先行） |
| **3** | 定義 | `src/config/killer_cut_archetypes.py` (新規) | バズる決めゴマ（冷酷な見下し、圧倒的破壊、絶望顔、返り血の微笑）辞書 |
| **4** | プロンプト | `prompts/templates/media/killer_cut_blueprint.j2` (新規) | 各話のクライマックスとなる1枚の絵面を先行定義するJinja2プロンプト |
| **5** | ロジック | `src/services/media/killer_cut_planner.py` (新規) | プロットから「見開きキラーコマ」の構図・演出を先行策定するサービス |
| **6** | テスト | `tests/unit/writing/test_comic_first_writer.py` (新規) | キラーカット逆算による本文執筆の単体テスト作成 |
| **7** | プロンプト | `prompts/templates/narrative/comic_first_writing.j2` (新規) | キラーカットへの視覚的コントラスト（表情変化・カメラ移動）を命じる執筆指示 |
| **8** | 執筆拡張 | `src/agents/writing/episode_writer.py` (修正) | キラーカット設計書を前提とした本文生成への対応 |
| **9** | 脚本同期 | `src/agents/media_script_agent.py` (修正) | 先行キラーカットを軸とした漫画ネーム（コマ割り）の自動連動生成 |
| **10** | 画像連動 | `src/agents/illustration_agent.py` (修正) | キラーカットのプロンプトをそのまま挿絵生成プロンプトへ自動ブリッジ |
| **11** | フロント | `frontend/src/components/media/ComicCutPreview.tsx` (新規) | 小説本文と連動した「今話の見開きキラーカット」プレビューUIコンポーネント |
| **12** | 統合検証 | `tests/e2e/test_comic_first_pipeline.py` (新規) | キラーカット策定 → 本文逆算執筆 → 漫画コマ割り・挿絵プロンプト連動E2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/comic_first.py`)
* **目標**: コミカライズ視点の決めゴマと本文演出の型を定義。
* **実装内容**:
  ```python
  from enum import Enum
  from pydantic import BaseModel, Field

  class VisualShotType(str, Enum):
      EXTREME_CLOSEUP = "extreme_closeup"  # 狂気を宿した瞳、震える唇
      LOW_ANGLE_FULL = "low_angle_full"    # 敵を見下ろす圧倒的な主人公
      HIGH_ANGLE_DESPAIR = "high_angle_despair" # 泥水に這いつくばる敵の無様な姿
      DOUBLE_PAGE_SPREAD = "double_page_spread" # 見開き全体を使った超絶大技の炸裂

  class KillerVisualCut(BaseModel):
      ep_num: int
      shot_type: VisualShotType
      character_expression: str = Field(..., description="表情の変化 (例: 嘲笑から完全な無感情への暗転)")
      lighting_and_atmosphere: str = Field(..., description="逆光、返り血、冷たい雨、魔法の閃光")
      visual_contrast_target: str = Field(..., description="対比となる周囲や敵のリアクション")
      image_prompt_en: str = Field(..., description="画像生成AIに直結する英語プロンプト")
  ```
* **受け入れ基準**: `mypy src/models/comic_first.py` がエラーなく通ること。

---

### Step 2: キラーカット策定テスト作成 (`tests/unit/media/test_killer_cut_planner.py`)
* **目標**: プロットの山場から最適な見開きカットが設計できるか検証。
* **実装内容**:
  - 追放ざまぁプロットに対し、「見下し・冷酷な笑顔」のキラーカットが選定されることを検証。
* **受け入れ基準**: テストファイルが正しく実行できること。

---

### Step 3: キラーカット典型パターン定義 (`src/config/killer_cut_archetypes.py`)
* **目標**: 商業マンガ・Webtoonで最もバズるビジュアルパターンのプリセット辞書。
* **実装内容**:
  ```python
  KILLER_CUT_ARCHETYPES = {
      "cold_gaze": {
          "shot_type": "low_angle_full",
          "expression": "一切の慈悲を捨てた、凍りつくような冷笑",
          "contrast": "命乞いをする元仲間が地面に額を擦り付ける構図",
      },
      "overwhelming_release": {
          "shot_type": "double_page_spread",
          "expression": "静かに人差し指を立てる主人公と、背後で天を覆い尽くす漆黒の魔力陣",
          "contrast": "強大さを誇っていた軍勢が一瞬で豆粒のように硬直する構図",
      },
  }
  ```
* **受け入れ基準**: 最低6種類のキラーカットパターンが定義されていること。

---

### Step 4: キラーカット先行定義プロンプト (`prompts/templates/media/killer_cut_blueprint.j2`)
* **目標**: 本文執筆の前に、その話で最も読者の目を釘付けにする1枚の絵面を出力させるテンプレート。
* **実装内容**:
  - 指示: 「もしこのエピソードがコミカライズ（Webtoon）されたら、読者がTwitterでスクリーンショットを拡散する決定的な1コマはどこか？ その1コマを極限のビジュアル解像度で定義せよ」
* **受け入れ基準**: テンプレートレンダリングが構文エラーなく動作すること。

---

### Step 5: キラーカット策定サービス (`src/services/media/killer_cut_planner.py`)
* **目標**: プロットを受け取り、該当話数の `KillerVisualCut` を確定するサービス。
* **実装内容**:
  - `plan_killer_cut(plot_data: dict) -> KillerVisualCut`
  - LLMを用いて、ストーリーの最重要アクションシーンから1枚の構図を決定。
* **受け入れ基準**: Step 2 のテストが GREEN になること。

---

### Step 6: 逆算執筆テスト作成 (`tests/unit/writing/test_comic_first_writer.py`)
* **目標**: キラーカットの情景が本文クライマックスに精密に描写されるか検証。
* **実装内容**:
  - キラーカットで指定された構図・表情（瞳のハイライトの消失、冷たい笑み）が本文中に現れることをアサート。
* **受け入れ基準**: テストが正しく実行できること。

---

### Step 7: キラーカット逆算執筆プロンプト (`prompts/templates/narrative/comic_first_writing.j2`)
* **目標**: キラーカットを物語の頂点（ピーク）として、そこへ向かうカメラワークと表情差分を本文に強制する。
* **実装内容**:
  - 指示: 「本エピソードの頂点は次の絵面です: 【{{ killer_cut.character_expression }}】【構図: {{ killer_cut.shot_type }}】」
  - 指示: 「この瞬間に向けて、直前の文章では『敵の慢心・嘲笑』を極限まで強調し、このコマで一気に『息が止まる静寂と絶望の視覚的落差』を刻め」
* **受け入れ基準**: テンプレートレンダリングが正常に動作すること。

---

### Step 8: EpisodeWriterへの統合 (`src/agents/writing/episode_writer.py`)
* **目標**: `EpisodeWriter.write()` に `killer_cut` コンテキストを注入。
* **実装内容**:
  - `context` 内に `killer_cut` が存在する場合、`comic_first_writing.j2` を自動結合して本文生成を実行。
* **受け入れ基準**: 既存の執筆ロジックを壊さずに新モードが動作すること。

---

### Step 9: MediaScriptAgent同期 (`src/agents/media_script_agent.py`)
* **目標**: 漫画コマ割り生成時、事前に決めたキラーカットを見開き大ゴマ（またはWebtoonの特大縦スクロールコマ）として固定配置。
* **実装内容**:
  - 生成されるコマ割りリスト（`panels`）の中で、クライマックスのコマに `is_killer_cut=True` と特大カメラアングルを付与。
* **受け入れ基準**: コマ割りデータにキラーカットが明示的に反映されること。

---

### Step 10: IllustrationAgent連携 (`src/agents/illustration_agent.py`)
* **目標**: `KillerVisualCut.image_prompt_en` をそのまま挿絵生成AI（Stable Diffusion / DALL-E / Midjourney等）へ渡せるようにブリッジ。
* **実装内容**:
  - `generate_scene_illustration` の入力プロンプトとしてキラーカットの英語プロンプトを最優先使用。
* **受け入れ基準**: 挿絵生成タスクでキラーカットのプロンプトが利用されること。

---

### Step 11: キラーコマプレビューUI (`frontend/src/components/media/ComicCutPreview.tsx`)
* **目標**: エディタの横で「今書いているエピソードの決定的な1コマ」をビジュアルカードとして確認できるUI。
* **実装内容**:
  - カメラ構図アイコン（ローアングル、クローズアップ等）。
  - キャラクターの表情差分指定、光と影の演出メモ。
  - 生成された挿絵があればインラインプレビュー。
* **受け入れ基準**: コンポーネントが単体でレンダリングできること。

---

### Step 12: E2E統合テスト (`tests/e2e/test_comic_first_pipeline.py`)
* **目標**: プロット → キラーカット策定 → 本文執筆 → 漫画コマ割り生成の一気通貫フローを検証。
* **実装内容**:
  - 生成された本文中にキラーカットの描写が含まれ、漫画台本にも大ゴマとして登録されていることを検証。
* **受け入れ基準**: `pytest tests/e2e/test_comic_first_pipeline.py` が ALL GREEN。
