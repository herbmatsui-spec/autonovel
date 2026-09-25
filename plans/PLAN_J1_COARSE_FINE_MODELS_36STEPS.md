# AutoNovel 実装計画書: Phase J1
# プロット二段階化 (Coarse-to-Fine) - モデルとプロンプトの分離 (36 Steps)

**目的**: 現行の `UltraFastPlotBatch` が抱える認知的過負荷（1話あたり30項目超×複数話）を解消するため、「大局骨子（Macro Skeleton）」と「微視的演出（Micro Blueprint）」のデータモデルおよびJinja2プロンプトテンプレートを安全に新設・分離する。  
**対象読者**: 小型・低性能LLM（Small LLM / 7Bクラス等）でも迷わず1ステップずつ順次実行できるように、ファイルパス、修正内容、テストケース名、検証コマンドを厳密に定義。

---

## 📋 全体構成（36ステップ）

- **Part 1 (Step 1-6)**: `EpisodeMacroSkeleton` および `PlotMacroBatch` モデルの定義と単体検証
- **Part 2 (Step 7-12)**: `PlotMicroBlueprint` モデルの定義と `MasterSceneBlock` / `SceneBeatBlock` 統合
- **Part 3 (Step 13-18)**: 既存 `PlotEpisode` との新モデル相互変換（マージ・スプリット）実装
- **Part 4 (Step 19-24)**: 大局骨子生成用 Jinja2 テンプレート `macro_plot_skeleton.j2` の新設と検証
- **Part 5 (Step 25-30)**: 微視的演出展開用 Jinja2 テンプレート `micro_scene_expander.j2` の新設と検証
- **Part 6 (Step 31-36)**: `PromptManager` へのビルダーメソッド追加と J1 総合テスト通過確認

---

## Part 1: `EpisodeMacroSkeleton` および `PlotMacroBatch` モデルの定義 (Step 1-6)

### Step 1: テストファイルの作成 `tests/unit/models/test_plot_coarse_fine.py`
- **目的**: 新設モデル用のテスト受け皿を作成する。
- **対象ファイル**: `tests/unit/models/test_plot_coarse_fine.py` (新規作成)
- **変更内容**: `pytest` のテストクラス `TestMacroSkeleton` の雛形を作成。
- **検証テスト**: `tests/unit/models/test_plot_coarse_fine.py`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py`

### Step 2: `EpisodeMacroSkeleton` モデルのインポートと基本定義
- **目的**: 大局骨子を表現する軽量な Pydantic モデルを定義。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**:
  ```python
  class EpisodeMacroSkeleton(BaseModel):
      ep_num: int = Field(..., description="エピソード話数")
      title: str = Field(default="", description="サブタイトル")
      one_line_summary: str = Field(default="", description="一行あらすじ")
      inciting_event: str = Field(default="", description="主要事件・発端")
      climax_payoff: str = Field(default="", description="山場・獲得物")
      tension: int = Field(default=50, ge=0, le=100, description="目標テンション")
      current_chain_phase: str = Field(default="Friction", description="感情チェーンフェーズ")
      resolution_style: str = Field(default="Cheat", description="解決スタイル")
      foreshadowing_plan: list[str] = Field(default_factory=list, description="関与する伏線ID")
      next_hook: CliffhangerDef = Field(default_factory=CliffhangerDef, description="クリフハンガー")
      model_config = MODEL_CONFIG_DEFAULTS
  ```
- **検証テスト**: `tests/unit/models/test_plot_coarse_fine.py::TestMacroSkeleton::test_create_macro_skeleton`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_create_macro_skeleton"`

### Step 3: `EpisodeMacroSkeleton` のバリデーションと型変換テスト
- **目的**: 数値文字列（`tension: "75"` 等）が自動で整数変換されることを保証。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: `tension` フィールドに `Annotated[int, BeforeValidator(extract_int)]` を適用。
- **検証テスト**: `TestMacroSkeleton::test_macro_skeleton_type_coercion`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_macro_skeleton_type_coercion"`

### Step 4: `PlotMacroBatch` バッチモデルの定義
- **目的**: 複数話の大局骨子を一括保持するコンテナモデルを定義。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**:
  ```python
  class PlotMacroBatch(BaseModel):
      episodes: list[EpisodeMacroSkeleton] = Field(default_factory=list)
      model_config = MODEL_CONFIG_DEFAULTS
  ```
- **検証テスト**: `TestMacroSkeleton::test_macro_batch_creation`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_macro_batch_creation"`

### Step 5: `PlotMacroBatch` の JSON アンラップ機構の追加
- **目的**: LLMが `{"metadata": {"episodes": [...]}}` や `{"data": [...]}` と返してきた場合のラッパー剥ぎ取り処理を実装。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: `@model_validator(mode="before")` による `unwrap_batch` メソッドを追加。
- **検証テスト**: `TestMacroSkeleton::test_macro_batch_unwrap`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_macro_batch_unwrap"`

### Step 6: `Part 1` 回帰テストの実行
- **目的**: Part 1 の全モデル定義が既存の `src/models/plot.py` を壊していないことを確認。
- **対象ファイル**: `tests/unit/models/test_plot.py`, `tests/unit/models/test_plot_coarse_fine.py`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py tests/unit/models/test_plot.py`

---

## Part 2: `PlotMicroBlueprint` モデルの定義 (Step 7-12)

### Step 7: `PlotMicroBlueprint` モデルの定義
- **目的**: 執筆直前に展開される微視的演出（3シーン×ビート）のモデルを定義。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**:
  ```python
  class PlotMicroBlueprint(BaseModel):
      ep_num: int = Field(..., description="エピソード話数")
      thought_process: str = Field(default="", description="前話からの接続・緩急の意図")
      detailed_blueprint: str = Field(default="", description="2000字詳細シーンフロー")
      scenes: list[MasterSceneBlock] = Field(default_factory=list, description="3シーン構成")
      bridge_from_previous: str = Field(default="", description="前話ラストからの接続指示")
      script_content: str = Field(default="", description="会話・行動台本")
      model_config = MODEL_CONFIG_DEFAULTS
  ```
- **検証テスト**: `tests/unit/models/test_plot_coarse_fine.py::TestMicroBlueprint::test_create_micro_blueprint`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_create_micro_blueprint"`

### Step 8: `PlotMicroBlueprint` の `MasterSceneBlock` 自動補完テスト
- **目的**: `scenes` が空リストの場合でもバリデーションエラーにならず、安全にハンドリングできることを確認。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: `scenes` のデフォルト値と `field_validator` を検証。
- **検証テスト**: `TestMicroBlueprint::test_micro_blueprint_empty_scenes`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_micro_blueprint_empty_scenes"`

### Step 9: `SceneBeatBlock` の五感・心理キーワード抽出保証
- **目的**: `PlotMicroBlueprint` 配下のビート群が既存の `SceneBeatBlock` と完全な互換性を持つことを検証。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: `SceneBeatBlock` のインスタンス化と `PlotMicroBlueprint.scenes[0].beats` への格納テスト。
- **検証テスト**: `TestMicroBlueprint::test_scene_beats_nested`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_scene_beats_nested"`

### Step 10: `PlotMicroBlueprint` の辞書展開（辞書からの生成）テスト
- **目的**: LLMの出力辞書から直接 `PlotMicroBlueprint.model_validate()` が成功することを検証。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: 辞書マッピングテストケースを `test_plot_coarse_fine.py` に追加。
- **検証テスト**: `TestMicroBlueprint::test_from_dict_parsing`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_from_dict_parsing"`

### Step 11: `PlotMicroBlueprint` の必須フィールドバリデーション
- **目的**: `ep_num` 欠落時に適切な `ValidationError` が発生することを確認。
- **対象ファイル**: `src/models/plot.py`
- **検証テスト**: `TestMicroBlueprint::test_required_fields`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_required_fields"`

### Step 12: `Part 2` 回帰テストの実行
- **目的**: Part 2 で追加されたモデルが正常に動作することを確認。
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "TestMicroBlueprint"`

---

## Part 3: 既存 `PlotEpisode` との新モデル相互変換 (Step 13-18)

### Step 13: マージ関数 `merge_macro_and_micro` の作成
- **目的**: 骨子（Macro）と肉付け（Micro）を合体して既存の `PlotEpisode` を生成するヘルパー関数を実装。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**:
  ```python
  def merge_macro_and_micro(macro: EpisodeMacroSkeleton, micro: PlotMicroBlueprint) -> PlotEpisode:
      # PlotCoreInfo, PlotAnalytics, MasterSceneBlock 等を統合して PlotEpisode を構築
  ```
- **検証テスト**: `tests/unit/models/test_plot_coarse_fine.py::TestMergeModels::test_merge_success`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_merge_success"`

### Step 14: マージ時の一貫性検証（話数不一致エラー）
- **目的**: `macro.ep_num != micro.ep_num` の場合に `ValueError` を投げる。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: `if macro.ep_num != micro.ep_num: raise ValueError(...)` を追加。
- **検証テスト**: `TestMergeModels::test_merge_ep_num_mismatch`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_merge_ep_num_mismatch"`

### Step 15: `PlotEpisode` から `EpisodeMacroSkeleton` への逆抽出（スプリット）
- **目的**: 既存の `PlotEpisode` から骨子情報だけを安全に抽出するメソッドを実装。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: `PlotEpisode.extract_macro_skeleton() -> EpisodeMacroSkeleton` を追加。
- **検証テスト**: `TestMergeModels::test_extract_macro_skeleton`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_extract_macro_skeleton"`

### Step 16: `PlotEpisode` から `PlotMicroBlueprint` への逆抽出（スプリット）
- **目的**: 既存の `PlotEpisode` から微視的演出情報だけを抽出するメソッドを実装。
- **対象ファイル**: `src/models/plot.py`
- **変更内容**: `PlotEpisode.extract_micro_blueprint() -> PlotMicroBlueprint` を追加。
- **検証テスト**: `TestMergeModels::test_extract_micro_blueprint`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_extract_micro_blueprint"`

### Step 17: ラウンドトリップ（分解→再合成）の等価性テスト
- **目的**: `PlotEpisode` → 分解（Macro + Micro） → マージ（`merge_macro_and_micro`）で情報損失がないことを検証。
- **対象ファイル**: `tests/unit/models/test_plot_coarse_fine.py`
- **検証テスト**: `TestMergeModels::test_roundtrip_merge`
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "test_roundtrip_merge"`

### Step 18: `Part 3` 相互変換の完全性確認
- **目的**: マージ・スプリットロジックの全件通過確認。
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py -k "TestMergeModels"`

---

## Part 4: Jinja2 テンプレート `macro_plot_skeleton.j2` の新設 (Step 19-24)

### Step 19: テンプレートファイル `prompts/templates/narrative/macro_plot_skeleton.j2` 作成
- **目的**: 大局骨子バッチ生成用の軽量プロンプトテンプレートを作成。
- **対象ファイル**: `prompts/templates/narrative/macro_plot_skeleton.j2` (新規作成)
- **変更内容**: 作品基本情報、ビートシート目標、対象話数リスト、出力JSONスキーマ（`PlotMacroBatch`）のみを指定。
- **検証テスト**: テンプレートファイルの存在確認

### Step 20: テンプレートレンダリング単体テストの作成
- **目的**: Jinja2 Environment から `macro_plot_skeleton.j2` がエラーなく読み込めることを確認。
- **対象ファイル**: `tests/unit/prompts/test_coarse_fine_templates.py` (新規作成)
- **変更内容**: `PromptRegistry` または `Environment` を用いてテンプレートロードをテスト。
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "test_render_macro_skeleton"`

### Step 21: `macro_plot_skeleton.j2` の入力変数バインド検証
- **目的**: `book_title`, `concept`, `ep_range`, `roadmap_items`, `schema_json` が正しく展開されるかテスト。
- **対象ファイル**: `prompts/templates/narrative/macro_plot_skeleton.j2`
- **検証テスト**: `test_render_macro_skeleton_variables`
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "test_render_macro_skeleton_variables"`

### Step 22: `macro_plot_skeleton.j2` の禁止事項（制約）の明示化
- **目的**: プロンプト内に「詳細なセリフやビートは記述不要。全体因果律とクリフハンガーに集中せよ」の制約を明記。
- **対象ファイル**: `prompts/templates/narrative/macro_plot_skeleton.j2`
- **検証テスト**: プロンプト文面検査テスト

### Step 23: 空データ耐性テスト（フォールバック表示）
- **目的**: `roadmap_items` が空リストの場合でもレンダリングがクラッシュしないことを確認。
- **対象ファイル**: `prompts/templates/narrative/macro_plot_skeleton.j2`
- **検証テスト**: `test_render_macro_skeleton_empty_roadmap`
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "test_render_macro_skeleton_empty_roadmap"`

### Step 24: `Part 4` テンプレート単体テスト通過確認
- **目的**: `macro_plot_skeleton.j2` のテスト全件通過。
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "macro"`

---

## Part 5: Jinja2 テンプレート `micro_scene_expander.j2` の新設 (Step 25-30)

### Step 25: テンプレートファイル `prompts/templates/narrative/micro_scene_expander.j2` 作成
- **目的**: 執筆直前の肉付け展開用プロンプトテンプレートを作成。
- **対象ファイル**: `prompts/templates/narrative/micro_scene_expander.j2` (新規作成)
- **変更内容**: 当該話の骨子、直前話末尾テキスト、登場キャラの俗物動機（Flaw）、3シーン×ビートの出力指示を定義。
- **検証テスト**: テンプレートファイルの存在確認

### Step 26: テンプレートレンダリング単体テストの作成
- **目的**: `micro_scene_expander.j2` が正常にロード・レンダリングされることをテスト。
- **対象ファイル**: `tests/unit/prompts/test_coarse_fine_templates.py`
- **検証テスト**: `test_render_micro_scene_expander`
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "test_render_micro_scene_expander"`

### Step 27: 直前話本文（`previous_ending_text`）の注入検証
- **目的**: 前話の生テキスト（末尾500文字）が正しくプロンプトに挿入されることを検証。
- **対象ファイル**: `prompts/templates/narrative/micro_scene_expander.j2`
- **検証テスト**: `test_render_micro_with_previous_text`
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "test_render_micro_with_previous_text"`

### Step 28: 描写演出指示（Show, Don't Tell）のプロンプト組み込み
- **目的**: 「各ビートに150文字以上の物理動作・五感キーワード・心理キーワードを含めよ」の厳格指示をテンプレートに配置。
- **対象ファイル**: `prompts/templates/narrative/micro_scene_expander.j2`
- **検証テスト**: プロンプト文面検査テスト

### Step 29: 第1話（前話なし）時のフォールバック分岐検証
- **目的**: `ep_num == 1`（前話が存在しない場合）に「第1話開幕インパクト」用の指示に自動分岐することを確認。
- **対象ファイル**: `prompts/templates/narrative/micro_scene_expander.j2`
- **検証テスト**: `test_render_micro_ep01_first_episode`
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "test_render_micro_ep01_first_episode"`

### Step 30: `Part 5` テンプレート単体テスト通過確認
- **目的**: `micro_scene_expander.j2` のテスト全件通過。
- **実行コマンド**: `pytest tests/unit/prompts/test_coarse_fine_templates.py -k "micro"`

---

## Part 6: `PromptManager` 統合と総合テスト (Step 31-36)

### Step 31: `PromptManager.build_macro_plot_skeleton_prompt` の実装
- **目的**: Python コードから `macro_plot_skeleton.j2` を簡単に呼び出せるビルダー関数を追加。
- **対象ファイル**: `prompts/manager.py`
- **変更内容**:
  ```python
  async def build_macro_plot_skeleton_prompt(self, bible_data: dict, ep_range: list[int], book_id: int | None = None) -> str:
      # context 構築と render_async 呼び出し
  ```
- **検証テスト**: `tests/unit/prompts/test_manager_coarse_fine.py::test_build_macro_prompt`
- **実行コマンド**: `pytest tests/unit/prompts/test_manager_coarse_fine.py -k "test_build_macro_prompt"`

### Step 32: `PromptManager.build_micro_scene_expander_prompt` の実装
- **目的**: Python コードから `micro_scene_expander.j2` を呼び出すビルダー関数を追加。
- **対象ファイル**: `prompts/manager.py`
- **変更内容**:
  ```python
  async def build_micro_scene_expander_prompt(self, macro_skeleton: dict, prev_ending_text: str, chars_data: list, book_id: int | None = None) -> str:
      # context 構築と render_async 呼び出し
  ```
- **検証テスト**: `tests/unit/prompts/test_manager_coarse_fine.py::test_build_micro_prompt`
- **実行コマンド**: `pytest tests/unit/prompts/test_manager_coarse_fine.py -k "test_build_micro_prompt"`

### Step 33: `PromptRegistry` のテンプレート自動検索パス確認
- **目的**: `macro_plot_skeleton.j2` と `micro_scene_expander.j2` が `PromptRegistry.fs_loader` で即座に検索可能であることを確認。
- **対象ファイル**: `prompts/registry.py`
- **検証テスト**: `tests/unit/prompts/test_registry.py`
- **実行コマンド**: `pytest tests/unit/prompts/test_registry.py`

### Step 34: 新旧モデルの相互排他・共存性検証
- **目的**: 既存の `UltraFastPlotBatch` や `PlotEpisode` が新モデルの追加によって一切影響を受けないことを確認。
- **対象ファイル**: `tests/unit/models/test_plot.py`
- **実行コマンド**: `pytest tests/unit/models/test_plot.py`

### Step 35: 型チェック (mypy) の通過確認
- **目的**: 追加したモデル・関数・型ヒントが mypy の型チェックを満たしていることを検証。
- **実行コマンド**: `mypy src/models/plot.py prompts/manager.py`

### Step 36: J1 総合テストスイート ALL GREEN 確認
- **目的**: Part 1〜6 で作成した全テストが 100% PASS することを確認。
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py tests/unit/prompts/test_coarse_fine_templates.py tests/unit/prompts/test_manager_coarse_fine.py`
