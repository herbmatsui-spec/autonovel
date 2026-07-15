# かんたんモード 50話自動生成 実装計画書

## 背景

現在のコードでは、かんたんモード（FullAutoWorkflow）で1作品50話を自動生成しようとしても、
以下の4つの問題により実質的に機能しない。

1. `WritingAgent.generate_episodes()` が最小コンテキストでLLMを呼び、プロット設計図を渡さない
2. `WritingAgent` に `planner` が注入されていないため、プロットのオンライン生成ができない
3. `PlotAgent._plot_expander` が `None` のため、`expand_plots()` が実行できない
4. `WritingPipeline` が存在するが未使用（デッドコード）

本計画書は、これらを72の小さなステップに分割し、確実に修正する。

---

## PHASE 1: WritingAgent コンテキスト拡充 (Steps 1-18)

### Step 1: `_get_plot()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: `book_id`, `branch_id`, `ep_num` を指定して `PlotDbModel` をDBから取得するメソッドを追加。
**テスト**: モックリポジトリでプロット取得を確認。

### Step 2: `_get_book()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: `book_id` から `BookDbModel` を取得するメソッドを追加。

### Step 3: `_get_chars()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: 作品に所属する全キャラクターをDBから取得するメソッドを追加。

### Step 4: `_get_prev_chapter()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: 前話の章データを取得するメソッドを追加（ep_num=1の場合はNone）。

### Step 5: `_get_active_chars()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: プロットに登場するキャラクター名から、アクティブなキャラクターを抽出するメソッドを追加。

### Step 6: `_build_char_static_ctx()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: キャラクターの不変属性（名前、外見、性格）を整形した文字列を生成するメソッドを追加。

### Step 7: `_build_char_dynamic_ctx()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: キャラクターの動的状態（現在の位置、所持品、ステータス）を整形するメソッドを追加。

### Step 8: `_build_prev_ctx()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: 前話までのあらすじや確定事実を整形した文字列を生成するメソッドを追加。

### Step 9: `_build_dialogue_profiles()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: 各キャラクターの話し方の癖を dict として生成するメソッドを追加。

### Step 10: `build_full_writing_context()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: Steps 1-9 のメソッドを統合し、`WritingContext` に必要な全フィールドを埋めた dict を返すメソッドを追加。

### Step 11: `generate_episodes()` でコンテキスト構築を置き換え
**ファイル**: `src/agents/writing.py`
**内容**: 最小コンテキスト `{"plot": {"branch_id": ..., "ep_num": ...}}` の代わりに `build_full_writing_context()` を呼ぶように変更。

### Step 12: `generate_episodes()` にプロット存在チェック追加
**ファイル**: `src/agents/writing.py`
**内容**: プロットがDBに存在しない場合、フォールバック処理を実行するように変更。

### Step 13: `write_episode()` のシグネチャ調整
**ファイル**: `src/agents/writing.py`
**内容**: `write_episode(book_id, ep_num, context)` が rich context を扱えるように、引数処理を調整。

### Step 14: `write_episode()` のプロンプト構築更新
**ファイル**: `src/agents/writing.py`
**内容**: `build_final_writing_prompt()` に渡す引数を、リッチコンテキストから取得するように更新。

### Step 15: DB取得失敗時のフォールバック追加
**ファイル**: `src/agents/writing.py`
**内容**: DB接続エラー時に最小コンテキストで動作するフォールバックを追加。

### Step 16: コンテキスト構築のロギング追加
**ファイル**: `src/agents/writing.py`
**内容**: 各コンテキスト取得ステップに debug ログを追加。

### Step 17: プロット検証ロジック追加
**ファイル**: `src/agents/writing.py`
**内容**: `detailed_blueprint` が空の場合、警告を出し `summary` をフォールバックとして使用。

### Step 18: `generate_episodes_pipeline()` の引数調整
**ファイル**: `src/agents/writing.py`
**内容**: `book_id` を内側の `generate_episodes()` 呼び出しに確実に渡すよう修正。

---

## PHASE 2: DefaultPlotExpander 実装 (Steps 19-28)

### Step 19: `src/services/default_plot_expander.py` 新規作成
**内容**: `DefaultPlotExpander` クラスのファイルを作成。`IPlotExpander` プロトコルを実装。

### Step 20: `__init__` 実装
**内容**: `repo`, `pm`, `llm` を依存注入として受け取る。

### Step 21: `expand_plots()` メソッドの枠組み実装
**内容**: メソッドシグネチャと基本的なエラー処理を実装。

### Step 22: バイブルJSON取得処理追加
**内容**: `repo.get_latest_bible()` でバイブルを取得し、JSON文字列化する処理を追加。

### Step 23: プロンプト構築処理追加
**内容**: `pm.build_ultra_fast_plot_batch_prompt()` でプロット生成プロンプトを構築する処理を追加。

### Step 24: LLM呼び出し処理追加
**内容**: `self.llm.generate_json(MODEL_PLOT_EXPANSION, prompt, response_schema=UltraFastPlotBatch)` を実行する処理を追加。

### Step 25: レスポンスパース処理追加
**内容**: `UltraFastPlotBatch.model_validate()` でパースし、plots リストを取得する処理を追加。

### Step 26: DB保存処理追加
**内容**: 各プロットを `repo.save_plot()` で保存するループを追加。

### Step 27: エラー handling 追加
**内容**: LLM失敗時の例外処理、部分成功時のリトライ、レポーターへの通知を追加。

### Step 28: ユニットテスト追加
**内容**: `tests/unit/test_default_plot_expander.py` を作成し、モックで動作確認。

---

## PHASE 3: PlotAgent DI 修正 (Steps 29-36)

### Step 29: `PlotAgent.__init__` の plot_expander を optional に
**ファイル**: `src/agents/plot.py`
**内容**: `plot_expander` のデフォルト値を `None` にし、必須でなくする。

### Step 30: PlotAgent にフォールバック_expander 注入
**ファイル**: `src/agents/plot.py`
**内容**: `__init__` 内で `plot_expander is None` の場合、`DefaultPlotExpander` を自動生成するフォールバックを追加。

### Step 31: `PlotAgent.expand_plots()` の委譲先確認
**ファイル**: `src/agents/plot.py`
**内容**: `self._plot_expander` が `None` でないことを保証するアサーションを追加。

### Step 32: container.py に DefaultPlotExpander インポート追加
**ファイル**: `src/core/container.py`
**内容**: `DefaultPlotExpander` をインポートする文を追加。

### Step 33: container.py の PlotAgent 生成を修正
**ファイル**: `src/core/container.py`
**内容**: `PlotAgent` 生成時に `plot_expander=DefaultPlotExpander(...)` を渡す。

### Step 34: PlotAgent 生成時の引数を確認
**ファイル**: `src/core/container.py`
**内容**: `PlotAgent` の `__init__` シグネチャと container の渡し方が一致するか確認。

### Step 35: container の wiring テスト実行
**内容**: `tests/unit/test_container.py` を実行し、PlotAgent の生成が成功することを確認。

### Step 36: PlotAgent スタンドアロンテスト
**内容**: モックリポジトリとモックLLMで `PlotAgent.expand_plots()` が動作することを確認。

---

## PHASE 4: WritingAgent Planner Injection (Steps 37-44)

### Step 37: `WritingAgent.__init__` に planner 引数追加
**ファイル**: `src/agents/writing.py`
**内容**: `planner` パラメータを `__init__` に追加し、`self._planner` に保存。

### Step 38: planner プロパティの確認
**ファイル**: `src/agents/writing.py`
**内容**: 既存の `planner` プロパティ（getter/setter、lines 100-105）が正しく動作するか確認。

### Step 39: container.py に PlanningAgent インポート追加
**ファイル**: `src/core/container.py`
**内容**: `PlanningAgent` をインポート（または既存の planner サービスを参照）。

### Step 40: container.py の WritingAgent 生成を修正
**ファイル**: `src/core/container.py`
**内容**: `WritingAgent` 生成時に `planner=planner` を渡す（container 内の planner サービスを使用）。

### Step 41: `_ensure_plot_exists()` メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: プロットがDBに存在するか確認し、存在しない場合は `self.planner.expand_plots()` で生成するメソッドを追加。

### Step 42: `_ensure_plot_exists()` のエラー処理
**ファイル**: `src/agents/writing.py`
**内容**: planner が `None` の場合のフォールバック、LLMエラー時のリトライを追加。

### Step 43: `generate_episodes()` で `_ensure_plot_exists()` 呼び出し追加
**ファイル**: `src/agents/writing.py`
**内容**: 各エピソード生成前に `_ensure_plot_exists()` を呼ぶように変更。

### Step 44: テスト更新
**内容**: `tests/` 配下の `WritingAgent` テストに `planner` モックを注入するよう更新。

---

## PHASE 5: StreamingPlotScheduler 統合 (Steps 45-54)

### Step 45: StreamingPlotScheduler のインポート追加
**ファイル**: `src/agents/writing.py`
**内容**: `from src.agents.writing_scheduler import StreamingPlotScheduler` を追加。

### Step 46: `generate_episodes_pipeline()` でスケジューラ初期化
**ファイル**: `src/agents/writing.py`
**内容**: パイプライン開始時に `StreamingPlotScheduler` を初期化するコードを追加。

### Step 47: arcs の取得処理追加
**ファイル**: `src/agents/writing.py`
**内容**: `repo.get_arcs(book_id)` で arcs を取得し、スケジューラに渡す。

### Step 48: プロット先行スケジュール追加
**ファイル**: `src/agents/writing.py`
**内容**: 現在のエピソード+1, +2 のプロット生成をスケジュールするコードを追加。

### Step 49: プロット待機処理追加
**ファイル**: `src/agents/writing.py`
**内容**: 各エピソード執筆前に `await scheduler.await_plot_ready(ep)` を呼ぶ。

### Step 50: タイムアウト設定追加
**ファイル**: `src/agents/writing_scheduler.py`
**内容**: `await_plot_ready()` にタイムアウト（例: 30秒）を追加し、超過時はフォールバック。

### Step 51: タスククリーンアップ追加
**ファイル**: `src/agents/writing.py`
**内容**: パイプライン完了後、未完了のスケジューラタスクをキャンセルする。

### Step 52: スケジューラ失敗時のフォールバック
**ファイル**: `src/agents/writing.py`
**内容**: スケジューラ初期化失敗時は同期プロット生成にフォールバックする。

### Step 53: プロット生成の進捗レポート追加
**ファイル**: `src/agents/writing.py`
**内容**: スケジューラによるプロット生成開始/完了を reporter に通知。

### Step 54: スケジューラのロギング追加
**ファイル**: `src/agents/writing_scheduler.py`
**内容**: スケジュール作成、待機、完了時のログを追加。

---

## PHASE 6: WritingPipeline 整理 (Steps 55-60)

### Step 55: WritingPipeline の使用箇所調査
**内容**: `grep -r "WritingPipeline" src/` で使用箇所を確認。

### Step 56: 削除判断とアーカイブ
**内容**: 使用箇所がないことを確認し、`writing_pipeline.py` を `archive/` に移動。

### Step 57: 関連インポートの削除
**内容**: `writing_pipeline.py` をインポートしているファイルを検索し、インポート文を削除。

### Step 58: PipelineStep 関連のクリーンアップ
**内容**: `PipelineStep`, `PlotReadyStep`, `PrefetchStep`, `ApplyPatchStep`, `DraftingStep` の参照を削除。

### Step 59: テストファイルの更新
**内容**: `writing_pipeline.py` を参照するテストを削除または更新。

### Step 60: インポートエラー確認
**内容**: `python -c "import src.agents.writing"` でインポートエラーがないことを確認。

---

## PHASE 7: FullAutoWorkflow 強化 (Steps 61-68)

### Step 61: WriteStep に事前プロット生成追加
**ファイル**: `src/services/auto_workflow_pipeline.py`
**内容**: `WriteStep.execute()` の執筆開始前に、未生成のプロットを一括生成する処理を追加。

### Step 62: プロット一括生成メソッド追加
**ファイル**: `src/agents/writing.py`
**内容**: `pregenerate_plots(book_id, start_ep, end_ep)` メソッドを追加。

### Step 63: 進捗レポート追加
**ファイル**: `src/services/auto_workflow_pipeline.py`
**内容**: プロット生成進捗を reporter に通知する。

### Step 64: リトライロジック追加
**内容**: プロット生成失敗時の自動リトライ（最大2回）を追加。

### Step 65: easy_mode パラメータ伝播確認
**内容**: `FullAutoWorkflow` から `generate_episodes_pipeline()` への `is_easy_mode` 伝播を確認。

### Step 66: プロット検証追加
**内容**: 執筆開始前に全エピソードのプロット存在を検証し、不足分をレポート。

### Step 67: バッチ生成の並列度調整
**内容**: 初期プロット生成の並列度を設定可能にする（現在は2並列）。

### Step 68: 部分失敗時の処理追加
**内容**: 一部エピソードのプロット生成のみ失敗した場合、その話をスキップして継続するか確認。

---

## PHASE 8: モデル参照クリーンアップ (Steps 69-72)

### Step 69: model_router.py の audit/marketing デフォルト更新
**ファイル**: `src/llm/model_router.py`
**内容**: `"audit": "gemini-2.0-flash"` → `"audit": "gemini-3.1-flash-lite"`、同様に marketing も更新。

### Step 70: retry_decorator.py のフォールバックモデル更新
**ファイル**: `src/services/retry_decorator.py`
**内容**: `MODEL_ULTRA_STABLE` と `MODEL_STABLE_FALLBACK` のフォールバック文字列を更新。

### Step 71: prompt_caching.py のデフォルトモデル更新
**ファイル**: `src/services/prompt_caching.py`
**内容**: 関数引数のデフォルトモデル名を更新。

### Step 72: plot_langgraph.py のモデル参照更新
**ファイル**: `src/backend/workflows/plot_langgraph.py`
**内容**: ハードコードされた `"gemini-2.0-flash"` を現行モデルに変更。

---

## 検証項目

- [ ] `python -m pytest tests/unit -q` がすべて pass
- [ ] `python -c "import src.agents.writing"` がエラーなく実行
- [ ] `python -c "import src.core.container"` がエラーなく実行
- [ ] `grep -r "gemini-2.0-flash" src/` が該当なし
- [ ] `grep -r "WritingPipeline" src/` が該当なし
- [ ] 3話分のミニ統合テストが成功

---

## 前提条件

- 企画モデルは既に `gemini-3.1-flash-lite` に差し替え済み
- `PlanStep` の `plan_auditor` バグは修正済み
- `DraftingStep` の引数バグは修正済み
- Google AI API キーが設定されていること
