# PLAN 07: 10万字中盤ダレ突破（第2アーク強制相転移） 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 長編構成・プロット展開エンジン  
**目的**: Web小説の9割が脱落する「第20〜30話（約5万字付近）の中弛み・目的喪失の死の谷」を突破し、商業単行本1巻分（約10〜12万字）をダレずに完走させるため、第2アーク強制相転移（Midpoint Catalyst）およびマイクロ・カタストロフィ注入機構を実装する。  
**前提**: 小型・低性能LLMでも迷わず1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/midpoint_catalyst.py` (新規) | 相転移イベント、テンション評価、第2アーク定義のPydanticモデル定義 |
| **2** | テスト | `tests/unit/narrative/test_tension_monitor.py` (新規) | 物語の緊張感低下・マンネリ検知ロジックの単体テスト作成（TDD先行） |
| **3** | ロジック | `src/services/narrative/tension_monitor.py` (新規) | 3話以上平穏または同一展開が続いた際の中弛み検知サービス |
| **4** | 定義 | `src/config/midpoint_events.py` (新規) | ゲームチェンジャー（新勢力乱入・代償発覚・拠点崩壊・真相露呈）プリセット集 |
| **5** | テスト | `tests/unit/narrative/test_midpoint_catalyst.py` (新規) | 第20〜25話での第2アーク相転移プロット生成のテスト作成 |
| **6** | プロンプト | `prompts/templates/narrative/midpoint_phase_shift.j2` (新規) | 物語の前提・スケールを1段階引き上げるJinja2プロンプト |
| **7** | ロジック | `src/services/narrative/midpoint_catalyst.py` (新規) | 第2アーク強制相転移イベント生成エンジン本体の実装 |
| **8** | 微細波乱 | `src/services/narrative/micro_catastrophe_injector.py` (新規) | 日常回に1話1つ不穏な予兆（マイクロ・カタストロフィ）を自動挿入する機能 |
| **9** | プロット結合 | `src/agents/plot.py` (修正) | 第20話以降のプロット生成時に相転移イベントを自動結合する改修 |
| **10** | 監査連動 | `src/agents/specialists/consistency_auditor.py` (修正) | 相転移による世界観拡張が第1部と矛盾しないか検証するルール追加 |
| **11** | フロント | `frontend/src/components/narrative/TensionCurveViewer.tsx` (新規) | 全話の緊張度推移と「中盤転換点」を表示するテンショングラフUI |
| **12** | 統合検証 | `tests/e2e/test_midpoint_phase_shift_pipeline.py` (新規) | 1話から40話までの通しプロット生成と第2アーク転換のE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: Pydanticモデル定義 (`src/models/midpoint_catalyst.py`)
* **目標**: 中盤相転移イベントとテンション監査のデータ構造を定義。
* **実装内容**:
  ```python
  from enum import Enum
  from pydantic import BaseModel, Field

  class CatalystType(str, Enum):
      INVADING_FORCE = "invading_force"       # チートが効かない新勢力・上位存在の乱入
      HIDDEN_PRICE = "hidden_price"           # 能力の代償・呪い・寿命制限の表面化
      SANCTUARY_LOST = "sanctuary_lost"       # 安住の地や拠点の崩壊・新大陸への移動
      WORLD_TRUTH = "world_truth"             # 世界の偽りや神々の陰謀の開示

  class PhaseShiftEvent(BaseModel):
      trigger_ep: int = Field(..., ge=20, le=30)
      catalyst_type: CatalystType
      disruption_summary: str = Field(..., description="主人公と世界を襲う決定的な激震")
      new_stakes: str = Field(..., description="第2アークで賭けられる新たな目標・危機")

  class EpisodeTensionScore(BaseModel):
      ep_num: int
      tension_level: float = Field(..., ge=0.0, le=100.0)
      is_stagnant: bool = False
  ```
* **受け入れ基準**: `mypy src/models/midpoint_catalyst.py` がエラーなく通ること。

---

### Step 2: テンション低下検知テスト作成 (`tests/unit/narrative/test_tension_monitor.py`)
* **目標**: 連続した平穏回（日常回）を検知して警告を出すテスト。
* **実装内容**:
  ```python
  from src.services.narrative.tension_monitor import check_pacing_stagnation
  from src.models.midpoint_catalyst import EpisodeTensionScore

  def test_detect_stagnant_episodes():
      history = [
          EpisodeTensionScore(ep_num=21, tension_level=30.0),
          EpisodeTensionScore(ep_num=22, tension_level=28.0),
          EpisodeTensionScore(ep_num=23, tension_level=32.0),
      ]
      is_stagnant, warning = check_pacing_stagnation(history)
      assert is_stagnant is True
      assert "中弛み" in warning or "停滞" in warning
  ```
* **受け入れ基準**: テストがモジュール未定義で正しく失敗すること。

---

### Step 3: テンション監視サービス (`src/services/narrative/tension_monitor.py`)
* **目標**: 各話のあらすじ・プロットから緊張度をスコアリングし、3話連続停滞をアラート。
* **実装内容**:
  - 各話の衝突（Conflict）の有無、生死の危機、社会的地位の揺らぎを評価。
  - 平均緊張度が40未満の連続を「停滞」と判定。
* **受け入れ基準**: Step 2 のテストが GREEN になること。

---

### Step 4: ゲームチェンジャープリセット (`src/config/midpoint_events.py`)
* **目標**: 物語のスケールを爆発させる相転移イベントのテンプレート定義。
* **実装内容**:
  ```python
  MIDPOINT_CATALYST_TEMPLATES = {
      "invading_force": {
          "title": "規格外の上位列強の強襲",
          "description": "主人公が無双していた地方領地に、帝国直属の『神滅騎士団』が理不尽な接収を宣告して現れる。",
      },
      "hidden_price": {
          "title": "神級スキルの不可逆な代償",
          "description": "無制限に使えていた万能スキルの使用ごとに、主人公の感覚器官が1つずつ永久封印されることが発覚する。",
      },
  }
  ```
* **受け入れ基準**: 4系統のプリセットが辞書として定義されていること。

---

### Step 5: 第2アーク相転移テスト作成 (`tests/unit/narrative/test_midpoint_catalyst.py`)
* **目標**: 第20話以降のプロットに相転移イベントが正しく織り込まれるかテスト。
* **実装内容**:
  - 既存プロットに対して第22話で `PhaseShiftEvent` が適用され、以降の目標が刷新されることを検証。
* **受け入れ基準**: テストファイルが作成され実行可能であること。

---

### Step 6: プロット相転移プロンプト (`prompts/templates/narrative/midpoint_phase_shift.j2`)
* **目標**: 物語の第2アーク突入を宣言し、新たな敵と目的を設定させるJinja2テンプレート。
* **実装内容**:
  - 指示: 「これまでの『初期状態での無双・ざまぁ』はここで一度完了しました。第2アークとして、より巨大な理不尽・世界の真実・新たな脅威を提示せよ」
  - 指示: 「主人公に『現状維持』を許すな。強制的に新たな行動を迫られる状況を構築せよ」
* **受け入れ基準**: テンプレートレンダリングが構文エラーなく動作すること。

---

### Step 7: 第2アーク相転移エンジン本体 (`src/services/narrative/midpoint_catalyst.py`)
* **目標**: 第20〜25話の間に、作品ジャンルに最も適した `PhaseShiftEvent` を自動選定・適用する。
* **実装内容**:
  - `generate_midpoint_shift(book_id: int, trigger_ep: int) -> PhaseShiftEvent`
  - 作品の世界観・キャラクター属性を参照して最適な相転移パターンをLLMで肉付け。
* **受け入れ基準**: Step 5 のテストが通過すること。

---

### Step 8: マイクロ・カタストロフィ注入ロジック (`src/services/narrative/micro_catastrophe_injector.py`)
* **目標**: 単調な日常回であっても、必ずラストに「不穏な影」を1つ落とす。
* **実装内容**:
  - 日常シーンのプロット末尾に「遠くで黒煙が上がった」「見慣れない鳥が不気味に啼いた」「通信用の魔導具が突然砕けた」等の不吉な予兆を強制挿入。
* **受け入れ基準**: 挿入後のプロットに予兆要素が含まれること。

---

### Step 9: PlotAgent統合 (`src/agents/plot.py`)
* **目標**: `PlotAgent` のプロット展開ループに `MidpointCatalyst` を接続。
* **実装内容**:
  - `ep_num == 22` の段階で相転移イベントを自動挿入し、第23〜40話のプロット概要（アーク）を自動再構成。
* **受け入れ基準**: 40話構成のプロット生成で22話に明らかな転換点が生成されること。

---

### Step 10: ConsistencyAuditor整合性ルール追加 (`src/agents/specialists/consistency_auditor.py`)
* **目標**: 新勢力や新設定の登場が、第1話〜第20話までの基本設定と矛盾していないか監査。
* **実装内容**:
  - 「新勢力の存在が世界の基本法則を破綻させていないか」「主人公の既知の能力と矛盾がないか」のチェックロジックを追加。
* **受け入れ基準**: 破綻した相転移設定が差し戻されること。

---

### Step 11: テンショングラフUI (`frontend/src/components/narrative/TensionCurveViewer.tsx`)
* **目標**: 全エピソードの感情・緊張度の起伏をグラフ表示し、第2アークの転換点を一目で確認できるUI。
* **実装内容**:
  - エピソード番号（横軸）× 緊張度（縦軸）の折れ線チャート。
  - 第22話付近に「第2アーク転換点」フラグを視覚表示。
* **受け入れ基準**: チャートコンポーネントが正常に描画できること。

---

### Step 12: E2E統合テスト (`tests/e2e/test_midpoint_phase_shift_pipeline.py`)
* **目標**: 40話分のプロット通し生成で、中弛み判定の回避と第2アーク転換の完了を検証。
* **実装内容**:
  - 全40話のプロット生成を実行 → 20〜30話の緊張度スコアが50以上を維持していることをアサート。
* **受け入れ基準**: `pytest tests/e2e/test_midpoint_phase_shift_pipeline.py` が ALL GREEN。
