# 官能特化型サブエージェント実装ロードマップ（実装計画書）

> **状態**: 計画のみ（実装未着手）
> **目的**: 既存プロジェクト（Kaku Hegemony v2 / claude2）に、NSFWモード時のみ動作する「官能特化型サブエージェント」を追加するための全工程計画。
> **方針原則**: NSFWトグが無効のときは一切の官能機能が露出・発動しない「オプトイン設計」。既存のSF/ファンタジー/ざまぁ系の文脈と分離し、後方互換性を保持する。

---

## 0. 現状分析と前提

### 0.1 既存コード配置の確認
- 定数・文体・アーキタイプ → 複数モジュール (`config/`)
  - ジャンル・アーキタイプ… [`config/archetypes.py`](config/archetypes.py:1)
    - ジャンル選択肢 → [`WIZARD_GENRE_OPTIONS`](config/archetypes.py:890)
    - EASY_MODE一括選択 → [`EASY_GENRES`](config/archetypes.py:930)
  - 文体・禁止語 → [`config/styles.py`](config/styles.py:1)
    - 文体定義 → [`STYLE_DEFINITIONS`](config/styles.py:1)（[`config/__init__.py`](config/__init__.py:8) で再エクスポート）
  - 基本定数 → [`config/base.py`](config/base.py:1)
- DB層
  - ORMモデル → [`src/backend/database/models.py`](src/backend/database/models.py:80) の [`Plot`](src/backend/database/models.py:80)
  - repo → [`src/backend/database/repositories/plot.py`](src/backend/database/repositories/plot.py:18) の [`PlotRepository`](src/backend/database/repositories/plot.py:18)
- ワークフロー / エージェント
  - ワークフロー種別 → [`streamlit_app/workflow_types.py`](streamlit_app/workflow_types.py:4) の [`WorkflowType`](streamlit_app/workflow_types.py:4)
  - 執筆エージェント → [`src/agents/writing.py`](src/agents/writing.py:25)
  - プロットエージェント → [`src/agents/plot.py`](src/agents/plot.py:11)
- UI
  - サイドバー（NSFWトグル想定） → [`streamlit_app/sidebar.py`](streamlit_app/sidebar.py:1)
  - プランニング → [`streamlit_app/ui_tabs_planning.py`](streamlit_app/ui_tabs_planning.py:1)
  - 執筆タブ → [`streamlit_app/ui_tabs_writing.py`](streamlit_app/ui_tabs_writing.py:1)
  - モニタ → [`streamlit_app/ui_tabs_monitor.py`](streamlit_app/ui_tabs_monitor.py:1)
  - 分析 → [`streamlit_app/ui_tabs_analytics.py`](streamlit_app/ui_tabs_analytics.py:1)

### 0.2 スコープ外
- 法規制の自動判定（最終パッケージの伏せ字生成は辞書ベースのみ）は jurisdictive な判断を含まず、プリセットの強度クラスタに紐付く変換テーブルのみを扱う。
- 18歳未満アクセス制限などの認証機能は本 roadmap の対象外（アプリ外の運用方針）。

---

## Phase 1: 基礎定義とインフラの拡張 (Steps 1-6)

### Step 1: [`config/base.py`](config/base.py:1) への官能ジャンル定数追加
- 変更対象: [`config/base.py`](config/base.py:1)
- 追加内容:
  ```python
  GENRE_EROTIC = "官能/ロマンス"
  EROTIC_INTENSITY_SCALE = {0:"ほのぼの", 1:"微熱", 2:"情熱", 3:"背徳", 4:"濃厚", 5:"過激"}
  DEFAULT_EROTIC_INTENSITY = 2
  NSFW_DEFAULT_ENABLED = False
  ```
- 影響範囲: import側で参照追加のみ。後方互換性あり。
- テスト観点: import時の AttributeError 発生なし。定数が enum でなく文字列なので EASY_GENRES との衝突確認。

### Step 2: [`config/`](config/styles.py:1) への文体定義 `STYLE_EROTIC_STANDARD` 追加
- 変更対象: [`config/styles.py`](config/styles.py:1) の [`STYLE_DEFINITIONS`](config/styles.py:1) へ追記。
  ※実体は search で確認済みだが、`STYLE_DEFINITIONS` の実体は styles.py 末尾付近にあるはず → 実装時に read で確認。
- 追加文体（情緒重視）:
  - トーン: "触覚・匂い・呼吸を主軸に、情緒と余韻を重んじ、直接的な露骨表現を控える"
  - 文禁ワード: 直情的な生殖器名称、AV志向の擬音語を「文学的比喩」へ置換する指示
  - ペーサー: 平均文長60〜110字、タメ→解放の呼吸 //ただし dolce > vivace
- 影響範囲: [`config/__init__.py`](config/__init__.py:8) の再エクスポートに追加。

### Step 3: [`EASY_GENRES`](config/archetypes.py:930) へ「官能/ロマンス」カテゴリ追加
- 変更対象: [`config/archetypes.py`](config/archetypes.py:930) の [`EASY_GENRES`](config/archetypes.py:930)
  および [`WIZARD_GENRE_OPTIONS`](config/archetypes.py:890)
- 追加内容:
  ```python
  "🌸 純愛官能":      {"genre": GENRE_EROTIC, "archetype": "純愛官能（情緒重視）", "auto_enabled": "nsfw_only"},
  "💜 背徳官能":      {"genre": GENRE_EROTIC, "archetype": "背徳官能（心理葛藤重視）", "auto_enabled": "nsfw_only"},
  ```
- 制御要件: `auto_enabled == "nsfw_only"` のエントリは、[`streamlit_app/sidebar.py`](streamlit_app/sidebar.py:1) のNSFWトグがOFFの時は [`ui_tabs_planning.py`](streamlit_app/ui_tabs_planning.py:1) の選択肢からフィルタされる。既存の `auto_enabled=True/False` との併存を壊さないため、三値 accepts as `bool|Literal["nsfw_only"]` へ変更。
- リスク: 既存 dict のバリデーションが `bool` を前提にしている箇所（[`config/validator.py`](config/validator.py:1)）を確認し、必要なら Literal 対応。

### Step 4: NSFWモード有効時のみ表示される警告・免責事節コンポーネント
- 新規ファイル: [`streamlit_app/ui/components/nsfw_disclaimer.py`](streamlit_app/ui/components/nsfw_disclaimer.py:1)
- 責務:
  - NSFWトグON時の初回表示時にモーダル/バーナー表示
  - 同意状態は [`storage/`](storage/session_state.json:1) のsession_stateに保存（再訪時の省力）
  - 18歳未満アクセス不可の案内、自己責任である旨、表現の強さを選択的にavenueする旨
- IF:
  ```python
  def render_nsfw_disclaimer() -> bool: ...  # True = consented
  ```
- 呼び出し元: [`streamlit_app/sidebar.py`](streamlit_app/sidebar.py:1) および [`streamlit_app/app.py`](streamlit_app/app.py:1) の初回起動時。

### Step 5: DB `plot` テーブルへ `erotic_intensity` カラム追加（マイグレーション）
- 変更対象:
   - ORM: [`src/backend/database/models.py`](src/backend/database/models.py:80) の [`Plot`](src/backend/database/models.py:80) → `Column(Integer, default=0)` 追加
   - Pydantic: [`src/models/api_schemas.py`](src/models/api_schemas.py:38) の [`PlotSchema`](src/models/api_schemas.py:38) に `erotic_intensity: Optional[int] = None`
   - Pydantic: [`src/models/db.py`](src/models/db.py:73) の [`PlotDbModel`](src/models/db.py:73) に `erotic_intensity: int = 0`
  - Repo: [`src/backend/database/repositories/plot.py`](src/backend/database/repositories/plot.py:18) の [`PlotRepository`](src/backend/database/repositories/plot.py:18) に upsert/getterで同カラムを取り扱うロジック追加
- マイグレーション:
  - [`alembic/`](alembic/1) 直下に新規 revision `add_erotic_intensity_to_plot` を作成。`ALTER TABLE plot ADD COLUMN erotic_intensity INTEGER DEFAULT 0 NOT NULL;`
  - downgrade: `DROP COLUMN erotic_intensity` (SQLiteの場合は batch mode 使用)
- 影響範囲: [`alembic/`](alembic/1) の head 更新。CIのマイグレーション試験が通ることを前提とする。
- リスク: SQLiteのbatch mode必須。PG環境では nullable=False制約の初期値 0 を付与して既存行を埋める手順を upgrade に含める。

### Step 6: [`streamlit_app/workflow_types.py`](streamlit_app/workflow_types.py:4) へ `EROTIC_REFINEMENT` 追加
- 変更対象: [`streamlit_app/workflow_types.py`](streamlit_app/workflow_types.py:4) の [`WorkflowType`](streamlit_app/workflow_types.py:4)
- 追加:
  ```python
  EROTIC_REFINEMENT = "erotic_refinement_workflow"
  ```
- および [`WORKFLOW_API_MAP`](streamlit_app/workflow_types.py:17) へ以下を追加:
  ```python
  WorkflowType.EROTIC_REFINEMENT: ("refine_erotic", ["book_id", "ep_num", "intensity", "platform_preset"])
  ```
- api_client側の実体は Phase 4 で実装（本Phaseでは宣言のみ）。

---

## Phase 2: 官能ナレッジベースの構築 (Steps 7-12)

### Step 7: 官能曲線（Erotic Pacing）モデルの定義
- 新規ファイル: [`config/erotic_pacing.py`](config/erotic_pacing.py:1)
- 用途: 「溜め（Tension/Desireの上昇）→ 頂点（Release）→ 余韻（Afterglow）」の3フェーズをガードするデータモデル。
- 仕様:
  ```python
  @dataclass
  class EroticBeat:
      phase: Literal["build", "peak", "afterglow"]
      desire_level: int           # 0-100
      sensory_focus: List[str]    # ["touch", "scent", "breath", "gaze", "sound"]
      consent_state: str          # "explicit", "implicit", "established"
  @dataclass
  class EroticCurve:
      beats: List[EroticBeat]
      target_intensity: int        # GENRE_EROTICから流用
  ```
- 出力: プロンプト生成（Phase 3）がこの曲線を inline でプロンプトに埋め込む。

### Step 8: [`STORY_ARCHETYPES`](config/archetypes.py:1) へ官能特化型を追加
- 変更対象: [`config/archetypes.py`](config/archetypes.py:1) の STORY_ARCHETYPES
- 追加 archetype:
  - `純愛官能`（情緒重視／同意明示／背徳なし）
  - `背徳官能`（タブー葛藤／心理負荷に上限設定）
  - `ファンタジー官能`（異種族／魔法による感覚の拡張，安全な非現実許容）
  - `夫婦/既婚官能`（親密性の深化／日常の情緒）
- 各 archetype は:
  - 推奨する [`STYLE_EROTIC_STANDARD`](config/styles.py:1) の亜種指定
  - 許可するボキャブラリショートカットを名前で参照
  - 設定される既定 [`erotic_intensity`](config/base.py:1) の上限・下限

### Step 9: 官能表現ボキャブラリーバンク
- 新規ファイル: [`config/erotic_vocabulary.py`](config/erotic_vocabulary.py:1)
- 内容:
  - 比喩表現メタファ（例：肌を「陶磁の表面」、欲望を「逆向きの波」など）
  - 擬音（文学訳：呼吸、衣擦れ、くぐもり音のみ。直接的な生殖器表記ではなく機能性の音）
  - 心理描写のテンプレ群：「陶酔」「自失」「背徳を忘れる」等の上位概念の物理化（[`FORBIDDEN_WORD_REPLACEMENTS`](config/styles.py:1) と整合）
- 設計: dict-like。erotic engine が [`random`](config/erotic_vocabulary.py:1) で選出するため、重み付けカテゴリ別のリスト構造。

### Step 10: 読者欲望（Desire）カテゴリの公式追加
- 変更対象: [`config/archetypes.py`](config/archetypes.py:1) に定義されている読者欲望群（[`CommercialRole`](config/archetypes.py:17) 併設 or 別リスト）
- 追加:
  - `官能` / `独占欲` / `背徳感` を正式ラベルとして登録
  - 既存traitと同様に、各 archetype がこれらを要求するか否かを宣言することを可能にする。
- 影響範囲: 推奨ルート、プロデューサー判定（Phase 6）が参照する一次元。

### Step 11: 同意・倫理境界を制御するセーフティ・メタプロンプト
- 新規ファイル: [`prompts/erotic/safety_manifest.md`](prompts/erotic/safety_manifest.md:1)
- 要件内容:
  - 同意が明示的／沈黙的かを scene prompt に問答式で確認させる。
  - 暴力的・非合意描写は [`erotic_intensity`](config/base.py:1) が `>=5` であっても硬く禁止する。
  - 「合法か否か」と「倫理学上妥当か否か」を分離し、倫理境界を超えないプロンプトを生成する（例：未成年・近親性強制の禁止）。
  - 実行時に必ず最初に展開される「プロローグ」としてマージされる。
- 統合: Phase 3 [`erotic_specialist.py`](src/engine/prompts/erotic_specialist.py:1) の全プロンプトに前置。

### Step 12: プラットフォーム別「表現の強さ」プリセット
- 新規ファイル: [`config/erotic_platform_presets.py`](config/erotic_platform_presets.py:1)
- プリセット例:
  - `kakuyomu_romance`（恋愛カテゴリ／作中の直接的官能はカット前提／[`erotic_intensity`](config/base.py:1)上限2）
  - `nocturn_novel`（ノクターン／R15程度／上限3）
  - `adult_selfhost`（自サイト/full／上限5）
- 内容: 許容語Top-Nのホワイト、必須変換パターン、[`erotic_intensity`](config/base.py:1) clamp範囲、伏字テンプレ参照。

---

## Phase 3: 専用プロンプトエンジンの開発 (Steps 13-18)

### Step 13: [`src/engine/prompts/erotic_specialist.py`](src/engine/prompts/erotic_specialist.py:1) 新規作成
- 責務: 官能シーン専用プロンプトビルダ。他engineからは選択的呼出のみ。
- 公開IF:
  ```python
  class EroticSpecialist:
      def build_scene_prompt(self, curve: EroticCurve, ctx: ...) -> str: ...
      def build_aftercare_prompt(self, ...) -> str: ...
      def metaphor_filter(self, raw_scene: str, intensity: int) -> str: ...
  ```
- 構成: Step 11 safety_manifest の強制プレフィックス、テンプレートJinja2、vocab bank参照。

### Step 14: 高解像度描写プロンプト（触覚・視覚・聴覚）
- 実装場所: Step 13 ファイル内の [`build_scene_prompt`](src/engine/prompts/erotic_specialist.py:1)
- 注力感覚: touch > scent ≒ sound > gaze > taste の優先序列を明示。
- 必須要素: 環境温度、衣装の断面／肌との境界、他者の呼吸の相をステップに分けて列挙。

### Step 15: 心理変化と肉体的反応の同期ロジック
- 実装: [`build_scene_prompt`](src/engine/prompts/erotic_specialist.py:1) 内に「感覚→解釈→評価→欲動」の4層フレームを内包。
- 出力時に各 beat に対して、心理フレームと身体的反応ペアを強制的に出力させる。

### Step 16: 比喩変換フィルター（文学的保持）
- 実装: [`metaphor_filter`](src/engine/prompts/erotic_specialist.py:1)
- 構成:
  - 禁止生語リスト → [`config/erotic_vocabulary.py`](config/erotic_vocabulary.py:1) の挿入候補から抽選
  - 強度ベースの正規表現置換（[`erotic_intensity`](config/base.py:1) <=2 なら更に上位概念に抽象化）
  - [`FORBIDDEN_WORD_REPLACEMENTS`](config/styles.py:1) と整合する拡張禁止表

### Step 17: アフターケア／余韻生成プロンプト
- 実装: [`build_aftercare_prompt`](src/engine/prompts/erotic_specialist.py:1)
- フェーズ: peak の直後に必ず生成される。感情の沈降、距離感の再設定、次話への余韻（伏線）を含む。
- long_tail: 1話あたり最低でも2パラを強制する。

### Step 18: Gemini セーフティフィルター緩和パラメータの最適化
- 変更対象: [`src/llm/gemini_provider.py`](src/llm/gemini_provider.py:1) に「NSFWモード時」の safety_settings プロファイル追加。
- 設計:
  - 通常時は既存 safety_settings を維持。
  - nsfw_profile 渡しがあったときのみ、[`HARM_CATEGORY_SEXUALLY_EXPLICIT`](src/llm/gemini_provider.py:1) を `BLOCK_ONLY_HIGH` に緩和（他は据え置きで安全第一）。
  - プロファイルは環境変数 `GEMINI_NSFW_PROFILE` で上書きを吞い込める構成（既定 off）。
- 安全装置: NSFW無効時は何があっても既存と同一。明示フラグ経由以外は無視。

---

## Phase 4: バックエンド・エージェントロジック (Steps 19-24)

### Step 19: [`UltimateHegemonyEngineProxy`](streamlit_app/proxy.py:1) に `generate_erotic_scene` 追加
- 変更対象: [`streamlit_app/proxy.py`](streamlit_app/proxy.py:1) の [`UltimateHegemonyEngineProxy`](streamlit_app/proxy.py:1)
- 署名:
  ```python
  async def generate_erotic_scene(self, book_id: int, ep_num: int, intensity: int = DEFAULT_EROTIC_INTENSITY) -> SceneResult:
  ```
- 処理:
  - [`Plot`](src/backend/database/models.py:80) の [`erotic_intensity`](config/base.py:1) が >0 であることを確認 → 0 なら fallback调用
  - [`EroticSpecialist`](src/engine/prompts/erotic_specialist.py:1) 生成、曲線の作成、要請、[`metaphor_filter`](src/engine/prompts/erotic_specialist.py:1) 適用 → 戻り
  - Auditへ通知

### Step 20: [`EpisodeWriter`](src/agents/writing.py:25) に官能サブエージェント委譲フック
- 変更対象: [`src/agents/writing.py`](src/agents/writing.py:25)
- 仕様:
  - 1話の中で、「官能シーンフラグ」が立っている beat に到達すると [`generate_erotic_scene`](streamlit_app/proxy.py:1) へ処理を委譲。
  - 委譲前後の文脈（前置/事後）は通常writerが維持。委譲範囲は beat単位で閉じる。
- NSFW無効時: フラグを無視し、通常の「情愛描写」にフォールバック（ボキャブラリバンクを非NSFW用サブセットに限定）。

### Step 21: 官能密度コントローラによる全体バランス調整
- 新規: [`src/services/erotic_density_controller.py`](src/services/erotic_density_controller.py:1)
- 仕様: book全体の [`erotic_intensity`](config/base.py:1) 平均値、連続する官能シーンの間隔を管理。
- ルール例: 連続3話巅峰 を禁ずる（肉体的疲労・心理的疲弊を避けるための cooldown 強制）。[`STRESS_FILLER_THRESHOLD`](config/base.py:59) の官能版 analogous。

### Step 22: 官能シーン矛盾検知ロジック
- 変更対象: [`src/agents/audit.py`](src/agents/audit.py:57) の [`PlotIntegrityMonitor`](src/agents/audit.py:57) 拡張
  または新規 [`src/agents/erotic_integrity.py`](src/agents/erotic_integrity.py:1)
- 検出:
  - 衣装の脱着整合性（前文で脱いだものが再び身についていないか）
  - 体位／位置関係の空間的整合性（左右・上下の逆転）
  - 制約（過去に定めた身体的特徴・禁忌）との不整合
- は BレベルIssueとして [`src/services/audit_service.py`](src/services/audit_service.py:1) に記録。

### Step 23: Huey バックグラウンドワーカーに「官能研磨」タスク登録
- 変更対象: 既存の Huey taskモジュール（[`src/services/`](src/services/writing_pipeline.py:1) 内のbackground定義）：[`src/services/writing_pipeline.py`](src/services/writing_pipeline.py:1) または[`scripts/`](scripts:1) の Huey設定。
- 追加 task: `refine_erotic_task(book_id, ep_num, intensity)`
- キュー名: `erotic` （隔離されたワーカ並列密度を別に設定可能にするため）。
- 目的: 重い [`metaphor_filter`](src/engine/prompts/erotic_specialist.py:1) / aftercare生成を非同期に。

### Step 24: [`streamlit_app/api_client.py`](streamlit_app/api_client.py:1) に官能エージェント呼出エンドポイント追加
- 変更対象: [`streamlit_app/api_client.py`](streamlit_app/api_client.py:1)
- 関数: `refine_erotic(book_id, ep_num, intensity, platform_preset)` （Step 6の [`WORKFLOW_API_MAP`](streamlit_app/workflow_types.py:17) と型整合）
- backend: [`src/backend/server.py`](src/backend/server.py) に対応エンドポイント `/api/refine_erotic` を追加。

---

## Phase 5: UI/UX とインタラクション (Steps 25-30)

### Step 25: [`ui_tabs_planning.py`](streamlit_app/ui_tabs_planning.py:1) に官能作品ウィザードページ
- 変更対象: [`streamlit_app/ui_tabs_planning.py`](streamlit_app/ui_tabs_planning.py:1)
- 新規セクション: NSFW有効時のみ「官能/ロマンス」を選択可能にした3ステップウィザード（ジャンル→アーキタイプ→強度）。
- 出力: [`Plot`](src/backend/database/models.py:80) 生成時に [`erotic_intensity`](config/base.py:1) を渡す。

### Step 26: [`ui_tabs_writing.py`](streamlit_app/ui_tabs_writing.py:1) に強度スライダー（0: ほのぼの 〜 5: 過激）
- 変更対象: [`streamlit_app/ui_tabs_writing.py`](streamlit_app/ui_tabs_writing.py:1)
- 追加: `st.slider("官能描写の強度", 0, 5, default=2)`。NSFW無効時は表示しないだけでなく、背後で `st.session_state["erotic_intensity"] = 0` を強制。
- 連携: 書き出し1話ごとに slider値を [`refine_erotic`](streamlit_app/api_client.py:1) へ渡す。

### Step 27: [`ui_tabs_monitor.py`](streamlit_app/ui_tabs_monitor.py:1) に官能曲線可視化グラフ
- 変更対象: [`streamlit_app/ui_tabs_monitor.py`](streamlit_app/ui_tabs_monitor.py:1)
- 追加: plotlyを用いた [`EroticCurve`](config/erotic_pacing.py:1)(build→peak→afterglowを縦軸) のエリアチャート。
- データソース: 完成エピソードから [`compute_curve_from_text`](src/services/erotic_density_controller.py:1) で抽出（score軽量版）。

### Step 28: 特定キーワード → 文学的表現へのワンクリック置換ボタン
- 実装: [`streamlit_app/ui_tabs_writing.py`](streamlit_app/ui_tabs_writing.py:1) の選択範囲の context-menu代替（Streamlitはネイティブ未対応なのでサイドパネル式）。
- 仕組み: 選択文字列を backendへ送り、[`metaphor_filter`](src/engine/prompts/erotic_specialist.py:1) を実行 → 置換デファクト案を3候補表示 → クリックで差替。

### Step 29: [`sidebar.py`](streamlit_app/sidebar.py:1) のNSFWトグによるテーマ切替（深紅/紫）
- 変更対象: [`streamlit_app/sidebar.py`](streamlit_app/sidebar.py:1) および [`streamlit_app/app.py`](streamlit_app/app.py:1)
- 方式: NSFW有効時にセッションstateを立て、[`pages_config.py`](streamlit_app/pages_config.py:1) or CSS injection で `--primary-color` などを「深紅(`#7b1518`)/紫(`#4b0f5e`)」に切替。
- 注意: 公序良俗の観点から、テーマ色は控えめに、安易に性的だと強調しない範囲で。

### Step 30: インポート機能の手書き官能原稿解析・研磨モード
- 変更対象: 既存のchapter import機能（[`workflow_types.py`](streamlit_app/workflow_types.py:46) の [`IMPORT_CHAPTER`](streamlit_app/workflow_types.py:13) 周辺）
- 追加: 「官能原稿モード」を選択した場合、[`metaphor_filter`](src/engine/prompts/erotic_specialist.py:1) + 整合性検知（Step 22）を import フローに挟む。

---

## Phase 6: 評価・最適化と品質管理 (Steps 31-36)

### Step 31: [`ui_tabs_analytics.py`](streamlit_app/ui_tabs_analytics.py:1) へ「官能度監査（Erotic Audit）」追加
- 変更対象: [`streamlit_app/ui_tabs_analytics.py`](streamlit_app/ui_tabs_analytics.py:1)
- 内容: 1エピソード中の「強度別語彙使用率」「曲線の偏り」「事後/余韻の有無」「タブー語使用回数」を一覧表示するダッシュボード。

### Step 32: AIプロデューサーによる「エロのタイミング」アドバイス
- 変更対象: 既存のプロデューサー判定サービス（[`src/services/audit_service.py`](src/services/audit_service.py:1) または [`scripts/generate_plot.py`](scripts/generate_plot.py:1) に同等のadvice機能）
- 追加ルール:
  - 続き3話のうち強度が4以上になる区間を検出 →「読者疲労の可能性」警告
  - 主軸プロット進行と重なる官能シーンは「心理負荷過多」と警告
  - アドバイスの生成自体は NSFW無効時点では呼ばれない（前提条件）

### Step 33: 官能表現の多様性スコア実装
- 新規: [`src/services/erotic_diversity_score.py`](src/services/erotic_diversity_score.py:1)
- 仕様:
  - トップN語の出現頻度の entropy
  - 同一比喩の反復使用率
  - 〔閾値未満〕→Step 16 filterの強度をあと1段階上げて再生成を提案

### Step 34: A/Bテスト機能での自己学習
- 拡張先: 既存のA/Bテスト基盤（[`src/services/prompt_version_service.py`](src/services/prompt_version_service.py:1) を想定）
- 方法: 強度2と3の2パターンを生成し、完読率/高評価率を撮る簡易仕組み（短期）。
- 判定: 統計的有意差検知までは足音段階、趨勢の記録のみ。

### Step 35: 最終パッケージ出力時の伏せ字自動生成
- 実装: [`formatters/`](formatters:1) 配下に [`erotic_censor.py`](formatters/erotic_censor.py:1) を新規設置。[`config/erotic_platform_presets.py`](config/erotic_platform_presets.py:1) のパターンテーブルに基づき、shading/伏字変換を施した2次ストリームを生成。
- 仕様:
  - 出力フォーマット: 平文 / カクヨム投稿用（`◆`区切り等）/ ノクターン用の3モード
  - 元テキストは保存し、伏せ字ストリームは別名で保存（`*_censored.txt`）

### Step 36: 全体の一貫テスト（プロット → 本文 → マケパック）
- ファイル: [`tests/integration/test_erotic_workflow.py`](tests/integration/test_erotic_workflow.py:1)
- 内容:
  - NSFW有効/無効両系での生成スモーク
  - [`EASY_GENRES`](config/archetypes.py:930) からの官能エントリ起点フルAUTO
  - 伏せ字ストリームの生成検証
  - erotic_intensityが0のbookでどの官能経路も発火しないことの検証

---

## 実装優先度と初期着手（"まずは、UI側から官能モードを認識できるように、設定と定数の追加から始めましょう"）

### 推奨着手順（Phase 1 最初の3ステップに絞った第一次パッチ）
1. **Step 1**: [`config/base.py`](config/base.py:1) へ [`GENRE_EROTIC`](config/base.py:1) 等の定数を追加。
2. **Step 2**: [`config/styles.py`](config/styles.py:1) の [`STYLE_DEFINITIONS`](config/styles.py:1) に [`STYLE_EROTIC_STANDARD`](config/styles.py:1) を追加し、[`config/__init__.py`](config/__init__.py:8) で再エクスポート。
3. **Step 3**: [`config/archetypes.py`](config/archetypes.py:930) の [`EASY_GENRES`](config/archetypes.py:930) / [`WIZARD_GENRE_OPTIONS`](config/archetypes.py:890) に `auto_enabled="nsfw_only"` エントリを追加し、[`config/validator.py`](config/validator.py:1) の型を `bool | Literal["nsfw_only"]` に緩和。

この第一次パッチは、UI（[`sidebar.py`](streamlit_app/sidebar.py:1), [`ui_tabs_planning.py`](streamlit_app/ui_tabs_planning.py:1)）から NSFWトグを認識するための最小構成である。これらが揃った時点で、NSFW無効時は官能選択肢が parse されない"ただの定義だけの世界"となり、後続Phaseが安全に上積みできる。

### 依存グラフ（要点）
```
Step1 (base.py) ──┐
                   ├─→ Step3 (archetypes) ──→ Step25 (UI wizard)
Step2 (styles)  ──┘
Step5 (DB) ─────────→ Step19 (proxy)  → Step20 (writer hook)
Step13 (prompt engine) ──→ Step14/15/16/17
Step11 (safety) ──→ Step13 / Step18
Step6 (WorkflowType) ──→ Step24 (api_client) ──→ Step23 (Huey)
```

---

## 未決項目（実装開始前にユーザ答えを確認すべき)

- **A**: ジャンル `GENRE_EROTIC` を既存ファンタジー系と同じ名前空間（[`WIZARD_GENRE_OPTIONS`](config/archetypes.py:890)）に置くか、それとも独立した `WIZARD_NSFW_GENRE_OPTIONS` に隔離するか。
- **B**: [`erotic_intensity`](config/base.py:1) は Bookレベル or Episodeレベル or Beatレベルのいずれに持たせるか（現状、本計画書は Plot/Epsodeレベルで円定格 - storage/dlはStep 5に準じる）。
- **C**: Gemini safety_settings プロファイルの変更を環境変数で gatingするが、本番運用設定（CIでの弾き）の有無。
- **D**: [`nsfw_default`](storage/session_default.json:1) への consent記録の永続化方式（ローカル localStorage に限るか、サーバ側保存を許容するか）。

以上、実装段階に入る前に上記4項目の合意取得を推奨する。
