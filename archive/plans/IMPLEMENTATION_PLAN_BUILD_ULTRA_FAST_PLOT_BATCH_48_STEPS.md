# build_ultra_fast_plot_batch_prompt 実装計画 (48ステップ)

## 概要
- **障壁**: `PromptManager.build_ultra_fast_plot_batch_prompt` が未実装
- **影響**: `tests/integration/test_workflow.py` の3テストがxfail
  - `test_full_auto_workflow_easy_mode` (#9)
  - `test_full_auto_workflow_normal_mode` (#10)
  - `test_full_auto_workflow_api_failure` (#11)
- **呼出箇所**: `src/services/bible_service.py:169`

## 呼出元の分析

```python
# src/services/bible_service.py:162-179
if config.initial_plot_limit > 0:
    ep_list = list(range(1, config.initial_plot_limit + 1))
    bible_json_str = json.dumps(bible_obj.model_dump(), ensure_ascii=False)
    sem = asyncio.Semaphore(2)

    async def _process_batch_item(ep_range):
        async with sem:
            # ★ ここで未実装メソッドが呼ばれる
            plot_prompt = await self.pm.build_ultra_fast_plot_batch_prompt(
                bible_json_str, ep_range, book_id=None
            )
            plot_res = await self.llm.generate_json(
                "gemini-2.0-flash", plot_prompt,
                response_schema=UltraFastPlotBatch, reporter=reporter
            )
            if not plot_res.success:
                raise RuntimeError(...)
            plots = UltraFastPlotBatch.model_validate(plot_res.metadata).plots
            for p in plots:
                await self.repo.save_plot(1, p.ep_num, p)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_process_batch_item([ep])) for ep in ep_list]
```

## 前提条件: 呼び出し契約

| パラメータ | 型 | 内容 |
|-----------|-----|------|
| `bible_json_str` | `str` | WorldBible 全体を JSON ダンプした文字列 |
| `ep_range` | `list[int]` | 例: `[1]` または `[1, 2]` |
| `book_id` | `int\|None` | オプション |

**戻り値**: `str` (プロンプト文字列)

**期待されるLLM応答**: `UltraFastPlotBatch` (Pydanticモデル)
```python
class UltraFastPlotBatch(BaseModel):
    plots: List[PlotEpisode]  # PlotEpisode は大量フィールドを持つ
```

## 48ステップ実装計画

### Phase 1: モデル・スキーマ調査 (Steps 1-8)

**Step 1**: `src/models/plot.py` の `PlotEpisodeBase` + `CoreEngineMixin` の全フィールドをリストアップする。`analytics` (PlotAnalytics), `core_info` (PlotCoreInfo), `foreshadowing` (PlotForeshadowing) などサブモデルの構造を確認する。

**Step 2**: `src/models/plot.py` の `PlotAnalytics` モデルを確認する。`tension`, `catharsis`, `is_catharsis`, `love_meter`, `catharsis_type`, `emotional_payoff`, `resolution_style`, `antagonist_status` などのフィールド 型を確認する。

**Step 3**: `src/models/plot.py` の `PlotCoreInfo` モデルを確認する。`ep_num`, `title`, `one_line_summary`, `detailed_blueprint`, `thought_process` フィールドを確認する。

**Step 4**: `src/models/plot.py` の `PlotForeshadowing` モデルを確認する。伏線関連のフィールド構造を確認する。

**Step 5**: `src/models/plot.py` の `EnigmaMixin` / `ComfortMixin` モデルを確認する。EnigmaAnalytics と ComfortAnalytics のフィールドを確認する。

**Step 6**: `src/models/plot.py` の `SceneBlock` / `MasterSceneBlock` モデルを確認する。`scenes` フィールドの構造を確認する。

**Step 7**: `prompts/templates/narrative/plot_expansion_prompt.j2` を再読し、existing テンプレートで使用されている変数と構造を確認する。これが `build_plot_expansion_prompt` と `build_ultra_fast_plot_batch_prompt` の主な参考テンプレートになる。

**Step 8**: `src/models/plot.py` の `UltraFastPlotBatch` が `List[PlotEpisode]` を期待していることを確認する。`PlotEpisode` が `PlotEpisodeBase[CoreEngineMixin] + EnigmaMixin + ComfortMixin` で構成されることを確認する。

### Phase 2: テンプレート設計 (Steps 9-16)

**Step 9**: `prompts/templates/narrative/ultra_fast_plot_batch_prompt.j2` という新規テンプレートファイルを作成する。ファイル名は `ultra_fast_plot_batch_prompt.j2` とする。

**Step 10**: テンプレートに以下の構造を設計する:
```
- 作品タイトル: {{ book_title }}
- ジャンル: {{ book_genre }}
- コンセプト: {{ concept }}
- スタイルキー: {{ style_key }}
- 主人公情報: {{ mc_profile }}
- サブキャラ情報: {{ sub_characters }}
- 世界設定: {{ world_settings }}
- 対象話数: {{ ep_range_str }} (例: 第1話, 第1-3話)
- 各話のロードマップ情報: {{ roadmap_items }}
- 出力スキーマ: {{ schema_json }}
```

**Step 11**: テンプレート内の `roadmap_items` セクションを設計する。各話に対する情報として `one_line_summary`, `resolution_style`, `burned_cost_or_loot`, `thematic_milestone`, `antagonist_status` を含める。

**Step 12**: テンプレートに `resolution_style` の許容値を明記する: `Cheat`, `Logic`, `Focus_Drama`。

**Step 13**: テンプレートに `PlotEpisode` の必須フィールド一覧を含める。`ep_num`, `title`, `one_line_summary`, `detailed_blueprint`, `scenes` (MasterSceneBlock のリスト), `thought_process`, `next_hook`, `tension`, `tension_delta`, `catharsis`, `is_catharsis`, `catharsis_type`, `love_meter`, `emotional_payoff`, `resolution_style`, `antagonist_status`, `burned_cost_or_loot`, `thematic_milestone`, `current_chain_phase`, `misunderstanding_gap`。

**Step 14**: テンプレートのプロンプト指示セクションを設計する:
```
指示:
1. 各話について PlotEpisode オブジェクトを生成せよ
2. 各PlotEpisode.detailed_blueprint は2000文字以上で、起承転結の流れを具体的に記述せよ
3. 各PlotEpisode.scenes は MasterSceneBlock のリストで、各シーンに action, dialogue_point, dramatic_function, emotional_payoff, beats を含めよ
4. beats の各項目は beat_type と action_description (150文字以上) を含めること
5. next_hook は読者が次をクリックしたくなるクリフハンガーを作成せよ
6. tension は 0-100 の整数、tension_delta は増減値、catharsis は 0-100、is_catharsis は真偽値
```

**Step 15**: テンプレートの最後に出力スキーマ (`UltraFastPlotBatch`) を JSON 形式で含める。

**Step 16**: テンプレートに few-shot 例 (例: 1話分の完全な PlotEpisode JSON) を含めるかを検討する。低性能LLM向け。

### Phase 3: PromptManager メソッド実装 (Steps 17-24)

**Step 17**: `prompts/manager.py` に `build_ultra_fast_plot_batch_prompt` メソッドを追加する。シグネチャ:
```python
async def build_ultra_fast_plot_batch_prompt(
    self,
    bible_json_str: str,
    ep_range: List[int],
    book_id: Optional[int] = None
) -> str:
```

**Step 18**: メソッド内で `bible_json_str` を `json.loads` でパースして `dict` に変換する。

**Step 19**: `bible_json_str` から `title`, `genre`, `concept`, `style_key`, `world_settings`, `mc_profile`, `sub_characters`, `full_story_roadmap` を抽出する。

**Step 20**: `ep_range` (例: `[1]` または `[1, 2, 3]`) から `ep_range_str` を生成する (例: `"第1話"` または `"第1話〜第3話"`)。

**Step 21**: `full_story_roadmap` から `ep_range` で指定された話数の `RoadmapItem` のみをフィルタリングする。

**Step 22**: フィルタリングした `RoadmapItem` をテンプレート用に辞書形式に変換する。`ep_num`, `one_line_summary`, `resolution_style`, `burned_cost_or_loot`, `thematic_milestone`, `antagon_status` を含める。

**Step 23**: `UltraFastPlotBatch` の JSON スキーマを取得して `schema_json` 変数に設定する。

**Step 24**: `self.render_async("ultra_fast_plot_batch_prompt.j2", {...})` を呼び出してプロンプト文字列を返す。

### Phase 4: PromptManager ヘルパー整備 (Steps 25-32)

**Step 25**: `build_ultra_fast_plot_batch_prompt` が使用するヘルパーメソッド `build_roadmap_item_context` を検討・必要に応じて実装する。

**Step 26**: `build_ultra_fast_plot_batch_prompt` 内で `world_settings` が辞書型の場合のハンドリングを追加する。`WorldBible.world_settings` は `WorldRules` モデルである場合がある。

**Step 27**: `mc_profile` が `CharacterRegistry` モデルの場合のハンドリングを追加する。テンプレート変数として適切に渡す。

**Step 28**: `sub_characters` が `List[CharacterRegistry]` の場合のハンドリングを追加する。

**Step 29**: `WorldRules` モデルの `model_dump()` が返す構造を確認し、テンプレート変数として適切に渡す。

**Step 30**: `book_id` が `None` の場合のデフォルト値を処理する (DB オーバーライドなし)。

**Step 31**: `render_async` に渡すコンテキスト dict が `UltraFastPlotBatch.schema_json()` を含んでいることを確認する。

**Step 32**: `render_async` のエラーハンドリングを追加する。テンプレートが存在しない場合はフォールバックを返す。

### Phase 5: フォールバック実装 (Steps 33-40)

**Step 33**: テンプレートファイルが存在しない場合のフォールバックプロンプトを実装する。`render_async` が失敗した場合にインラインでプロンプト文字列を生成する。

**Step 34**: フォールバックプロンプトの内容を決定する。以下の要素を含める:
```
- 作品タイトル、ジャンル、コンセプト
- 主人公情報 (name, surface_persona, inner_conflict, iron_constraint)
- 対象話数とロードマップ情報
- PlotEpisode 全フィールドの説明
- UltraFastPlotBatch スキーマ
```

**Step 35**: フォールバックプロンプトにも `resolution_style` の許容値を明記する。

**Step 36**: フォールバックプロンプトの文字数が十分に多いことを確認する (低性能LLM向け)。

**Step 37**: フォールバックプロンプトとテンプレートレンダリングの結果整合性を確認する。

**Step 38**: 例外ケースを処理する: `bible_json_str` が不正な JSON の場合。

**Step 39**: 例外ケースを処理する: `ep_range` が空リストの場合。

**Step 40**: 例外ケースを処理する: `full_story_roadmap` が空または不足している場合。

### Phase 6: 統合・動作確認 (Steps 41-48)

**Step 41**: `build_ultra_fast_plot_batch_prompt` を `PromptManager` クラスのメソッドとして追加する。

**Step 42**: テストを実行して `build_ultra_fast_plot_batch_prompt` がエラーを起こさずプロンプト文字列を返すことを確認する。

**Step 43**: テンプレートファイル `ultra_fast_plot_batch_prompt.j2` を `prompts/templates/narrative/` に作成する (まだの場合)。

**Step 44**: テスト `test_full_auto_workflow_easy_mode` をxfail 解除して実行する。

**Step 45**: テスト `test_full_auto_workflow_normal_mode` をxfail 解除して実行する。

**Step 46**: テスト `test_full_auto_workflow_api_failure` をxfail 解除して実行する。

**Step 47**: 3テスト全てが PASS することを確認する。失敗した場合はどのフィールドが足りないか確認してテンプレートまたはメソッドを修正する。

**Step 48**: 修正後、`pytest tests/integration/test_workflow.py -v` を実行して全テスト PASS + 0 xfail を確認して CI green を維持する。

## 重要: テストmockとの整合性

テストのmockは以下を期待している:
- `mock_llm.add_json_response("plot_expansion_prompt", {...})` — ここで `plot_expansion_prompt` は `build_ultra_fast_plot_batch_prompt` が返すプロンプトに対する応答
- 応答の形式: `PlotEpisode` オブジェクトのフィールドを持つ辞書
- `ep_num`, `title`, `one_line_summary`, `detailed_blueprint`, `scenes`, `tension`, `tension_delta`, `catharsis`, `is_catharsis`, `catharsis_type`, `love_meter`, `emotional_payoff`, `resolution_style`, `antagonist_status`, `next_hook`, `current_chain_phase`, `thought_process` が必須

## 失敗時のトラブルシュート

| エラー | 原因 | 対策 |
|--------|------|------|
| `AttributeError: 'NoneType' object has no attribute 'model_dump'` | `bible_json_str` が `None` | `bible_obj.model_dump()` が `None` を返さないことを確認 |
| `UltraFastPlotBatch.model_validate` で Validation Error | LLM応答不足フィールド | テンプレートの必須フィールド説明を確認 |
| `resolution_style` validation error | 許可されていない値 | テンプレートに `Cheat\|Logic\|Focus_Drama` を明記 |
| テンプレートなしエラー | `render_async` 失敗 | フォールバック実装で回避 |

## 次のアクション
1. Steps 1-8: モデル・スキーマ調査を実行
2. Steps 9-16: テンプレート設計・作成
3. Steps 17-24: `PromptManager` にメソッド追加
4. Steps 25-40: ヘルパー・フォールバック実装
5. Steps 41-48: 統合・テスト実行