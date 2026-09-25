# AutoNovel 実装計画書: Phase J3
# プロット二段階化 (Coarse-to-Fine) - パイプライン統合と総合検証 (36 Steps)

**目的**: 既存の `UltraFastPlotBatch` 依存箇所（`PlanStep`, `EasyModePipeline`, `FullAutoWorkflow`）を安全に二段階パイプラインへ切り替え、ビート描写解像度の向上をベンチマークで定量検証するとともに、既存システムへの完全なリグレッションフリーを確立する。  
**対象読者**: 小型・低性能LLM（Small LLM / 7Bクラス等）でも迷わず1ステップずつ順次実行できるように、ファイルパス、修正内容、テストケース名、検証コマンドを厳密に定義。

---

## 📋 全体構成（36ステップ）

- **Part 1 (Step 1-6)**: `PlanStep` の二段階化対応（骨子バッチ生成への切替）
- **Part 2 (Step 7-12)**: `WriteStep` と JIT Expander の本番パイプライン統合
- **Part 3 (Step 13-18)**: `EasyMode` / `FullAutoWorkflow` のシームレス切替
- **Part 4 (Step 19-24)**: ビート描写密度（Show率・五感タグ・文字数）ベンチマーク構築
- **Part 5 (Step 25-30)**: E2E 統合シミュレーションテスト（SQLite / Postgres 疎通）
- **Part 6 (Step 31-36)**: 全体リグレッション検証（全テスト ALL GREEN）とドキュメント同期

---

## Part 1: `PlanStep` の二段階化対応 (Step 1-6)

### Step 1: `PlanStep` テストファイルの作成 `tests/unit/pipeline/test_plan_step_coarse_fine.py`
- **目的**: 二段階化に対応した `PlanStep` の単体テストを作成。
- **対象ファイル**: `tests/unit/pipeline/test_plan_step_coarse_fine.py` (新規作成)
- **変更内容**: `PlanStep.execute` の実行時に大局骨子（Macro Skeleton）が正常生成・保存されるかをテスト。
- **実行コマンド**: `pytest tests/unit/pipeline/test_plan_step_coarse_fine.py`

### Step 2: `PlanStep.execute` 内のプロット展開呼び出しの切り替え
- **目的**: 重い `expand_plots`（一発全詳細展開）から `expand_macro_skeletons`（骨子バッチ展開）へ切り替え。
- **対象ファイル**: `src/services/pipeline_steps.py`
- **変更内容**:
  ```python
  # 変更前: await engine.planner.expand_plots(...)
  # 変更後:
  if hasattr(engine.plot_expander, "expand_macro_skeletons"):
      await engine.plot_expander.expand_macro_skeletons(
          book_id=ctx.book_id, target_ep_list=list(range(1, ctx.target_eps + 1)), reporter=reporter
      )
  ```
- **検証テスト**: `test_plan_step_executes_macro_expansion`
- **実行コマンド**: `pytest tests/unit/pipeline/test_plan_step_coarse_fine.py -k "test_plan_step_executes_macro_expansion"`

### Step 3: `WorkflowContext` への骨子メタデータの格納
- **目的**: 企画フェーズ終了時に、生成された骨子リストの概要を `ctx.metadata["macro_skeletons"]` に保持。
- **対象ファイル**: `src/services/pipeline_steps.py`
- **検証テスト**: `test_plan_step_populates_context_metadata`
- **実行コマンド**: `pytest tests/unit/pipeline/test_plan_step_coarse_fine.py -k "test_plan_step_populates_context_metadata"`

### Step 4: 後方互換性フラグ `use_coarse_fine_plot` の導入
- **目的**: 設定ファイルまたはコンテキストで二段階化の ON/OFF を切り替え可能にする（安全装置）。
- **対象ファイル**: `src/services/pipeline_base.py`, `config/settings.py`
- **変更内容**: `WorkflowContext.use_coarse_fine_plot: bool = True` を追加。
- **検証テスト**: `test_plan_step_toggle_backward_compatibility`
- **実行コマンド**: `pytest tests/unit/pipeline/test_plan_step_coarse_fine.py -k "test_plan_step_toggle_backward_compatibility"`

### Step 5: 旧方式（`use_coarse_fine_plot=False`）フォールバックの動作検証
- **目的**: フラグを False に倒した場合、従来の `UltraFastPlotBatch` がそのまま動作することを確認。
- **対象ファイル**: `src/services/pipeline_steps.py`
- **検証テスト**: `test_plan_step_legacy_fallback`
- **実行コマンド**: `pytest tests/unit/pipeline/test_plan_step_coarse_fine.py -k "test_plan_step_legacy_fallback"`

### Step 6: `Part 1` テスト通過確認
- **目的**: `PlanStep` の切り替えテスト全件通過。
- **実行コマンド**: `pytest tests/unit/pipeline/test_plan_step_coarse_fine.py`

---

## Part 2: `WriteStep` と JIT Expander 統合 (Step 7-12)

### Step 7: `WriteStep` テストファイルの作成 `tests/unit/pipeline/test_write_step_coarse_fine.py`
- **目的**: 執筆フェーズにおける JIT 展開と執筆の協調をテスト。
- **対象ファイル**: `tests/unit/pipeline/test_write_step_coarse_fine.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/pipeline/test_write_step_coarse_fine.py`

### Step 8: `WriteStep.execute` における JIT 展開の保証
- **目的**: 各エピソードの執筆前に `ensure_detailed_plot` が確実にコールされることを担保。
- **対象ファイル**: `src/services/pipeline_steps.py`
- **変更内容**: `WriteStep` のループ内、または委譲先 `engine.writer` で JIT 展開が発火することを確認。
- **検証テスト**: `test_write_step_triggers_jit_expansion`
- **実行コマンド**: `pytest tests/unit/pipeline/test_write_step_coarse_fine.py -k "test_write_step_triggers_jit_expansion"`

### Step 9: 前話本文が未存在の場合（第1話）の安全動作検証
- **目的**: 第1話の執筆時、前話本文なしで正常に JIT 展開が行われることを確認。
- **対象ファイル**: `src/services/pipeline_steps.py`
- **検証テスト**: `test_write_step_first_episode_safety`
- **実行コマンド**: `pytest tests/unit/pipeline/test_write_step_coarse_fine.py -k "test_write_step_first_episode_safety"`

### Step 10: 【デメリット2対策検証】投機的プリフェッチの統合検証
- **目的**: 第1話の執筆中に第2話のビート展開タスクが非同期に走り、第2話の待機時間が解消されることをテスト。
- **対象ファイル**: `src/services/pipeline_steps.py`
- **検証テスト**: `test_write_step_prefetch_integration`
- **実行コマンド**: `pytest tests/unit/pipeline/test_write_step_coarse_fine.py -k "test_write_step_prefetch_integration"`

### Step 11: 執筆失敗・リトライ時の詳細プロット再利用検証
- **目的**: 本文執筆がエラーでリトライされた際、JIT展開済みプロットが再利用され、二重展開が起きないことを検証。
- **対象ファイル**: `src/services/pipeline_steps.py`
- **検証テスト**: `test_write_step_retry_reuses_expanded_plot`
- **実行コマンド**: `pytest tests/unit/pipeline/test_write_step_coarse_fine.py -k "test_write_step_retry_reuses_expanded_plot"`

### Step 12: `Part 2` テスト通過確認
- **目的**: `WriteStep` 統合テスト全件通過。
- **実行コマンド**: `pytest tests/unit/pipeline/test_write_step_coarse_fine.py`

---

## Part 3: `EasyMode` / `FullAutoWorkflow` 切替 (Step 13-18)

### Step 13: `EasyModePipeline` の二段階化対応テスト
- **目的**: かんたんモード（`EasyMode`）で二段階プロットが完全に機能することをテスト。
- **対象ファイル**: `tests/unit/easy_mode/test_easy_mode_coarse_fine.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/easy_mode/test_easy_mode_coarse_fine.py`

### Step 14: `create_easy_mode_pipeline` のファクトリ更新
- **目的**: `src/services/auto_workflow_pipeline.py` において、`create_easy_mode_pipeline` に `DefaultPlotExpander` を正しく注入。
- **対象ファイル**: `src/services/auto_workflow_pipeline.py`
- **変更内容**: 依存関係注入（DI）の整理。
- **検証テスト**: `test_create_easy_mode_pipeline_has_expander`
- **実行コマンド**: `pytest tests/unit/easy_mode/test_easy_mode_coarse_fine.py -k "test_create_easy_mode_pipeline_has_expander"`

### Step 15: `FullAutoWorkflow` のファクトリ更新
- **目的**: `create_full_auto_pipeline` にも同様に二段階プロット展開を適用。
- **対象ファイル**: `src/services/auto_workflow_pipeline.py`
- **検証テスト**: `test_create_full_auto_pipeline_coarse_fine`
- **実行コマンド**: `pytest tests/unit/easy_mode/test_easy_mode_coarse_fine.py -k "test_create_full_auto_pipeline_coarse_fine"`

### Step 16: `SpiceGuard` と JIT 詳細プロットの協調確認
- **目的**: JIT展開されたビートの `psychological_layer` や `sensory_keywords` が `SpiceGuard` の保護対象として正しく認識されるか検証。
- **対象ファイル**: `src/easy_mode/spice_guard.py`
- **検証テスト**: `test_spice_guard_cooperation_with_jit_plot`
- **実行コマンド**: `pytest tests/unit/easy_mode/test_easy_mode_coarse_fine.py -k "test_spice_guard_cooperation_with_jit_plot"`

### Step 17: ワンクリック納品（ZIP/EPUB出力）のデータ完全性確認
- **目的**: 二段階化後も、生成された小説ZIP/EPUBに完全なプロット情報が含まれていることを検証。
- **対象ファイル**: `src/services/marketing/export_package.py`
- **検証テスト**: `test_export_package_includes_coarse_fine_plot`
- **実行コマンド**: `pytest tests/unit/easy_mode/test_easy_mode_coarse_fine.py -k "test_export_package_includes_coarse_fine_plot"`

### Step 18: `Part 3` テスト通過確認
- **目的**: EasyMode / FullAuto 統合テスト全件通過。
- **実行コマンド**: `pytest tests/unit/easy_mode/test_easy_mode_coarse_fine.py`

---

## Part 4: ビート描写密度ベンチマーク構築 (Step 19-24)

### Step 19: ベンチマークスクリプト `benchmarks/bench_plot_resolution.py` の作成
- **目的**: 現行の一発展開 vs 二段階展開の品質とパフォーマンスを比較計測するツールを作成。
- **対象ファイル**: `benchmarks/bench_plot_resolution.py` (新規作成)
- **変更内容**: 以下の指標を計測する関数を実装：
  1. `beat_word_count`: 各ビートの平均文字数（目標150字以上）
  2. `sensory_tag_coverage`: 五感タグ（視覚・聴覚・嗅覚・触覚・味覚）の網羅率
  3. `show_vs_tell_ratio`: 「〜した」等の要約型記述（Tell）に対する具体的描写（Show）の比率
  4. `llm_success_rate`: JSONバリデーションエラー発生率
- **実行コマンド**: `python benchmarks/bench_plot_resolution.py --dry-run`

### Step 20: ビート文字数の計測テスト
- **目的**: 二段階展開によってビート1つあたりの記述文字数が 1.5倍〜2倍 に増加することを検証。
- **対象ファイル**: `benchmarks/bench_plot_resolution.py`
- **検証テスト**: 単体テスト `test_benchmark_beat_word_count`
- **実行コマンド**: `pytest benchmarks/ -k "test_benchmark_beat_word_count"`

### Step 21: 五感タグ充足率の計測テスト
- **目的**: 3シーンすべてにおいて五感タグが最低2つ以上埋まっていることを確認。
- **対象ファイル**: `benchmarks/bench_plot_resolution.py`
- **検証テスト**: `test_benchmark_sensory_coverage`
- **実行コマンド**: `pytest benchmarks/ -k "test_benchmark_sensory_coverage"`

### Step 22: バリデーション失敗率の比較テスト
- **目的**: 複数話一括生成時のスキーマ欠落が、二段階化によって 0% に低減されることを実証。
- **対象ファイル**: `benchmarks/bench_plot_resolution.py`
- **検証テスト**: `test_benchmark_schema_validation_rate`
- **実行コマンド**: `pytest benchmarks/ -k "test_benchmark_schema_validation_rate"`

### Step 23: トータルレイテンシの比較計測
- **目的**: デメリット対策（投機的プリフェッチ＋小型モデル）により、体感待ち時間が増加していないことを計測。
- **対象ファイル**: `benchmarks/bench_plot_resolution.py`
- **検証テスト**: `test_benchmark_total_latency`
- **実行コマンド**: `pytest benchmarks/ -k "test_benchmark_total_latency"`

### Step 24: `Part 4` ベンチマークテスト通過確認
- **目的**: ベンチマークツールの単体動作確認。
- **実行コマンド**: `pytest benchmarks/ -k "plot"`

---

## Part 5: E2E 統合シミュレーションテスト (Step 25-30)

### Step 25: E2E シミュレーションテスト作成 `tests/e2e/test_coarse_fine_e2e.py`
- **目的**: 企画から本文生成、エクスポートまで完走する真のE2Eテストを作成。
- **対象ファイル**: `tests/e2e/test_coarse_fine_e2e.py` (新規作成)
- **実行コマンド**: `pytest tests/e2e/test_coarse_fine_e2e.py`

### Step 26: 3話連続生成の完全完走テスト（SQLite）
- **目的**: ローカル SQLite 環境で第1話〜第3話が二段階プロットで完走することを検証。
- **対象ファイル**: `tests/e2e/test_coarse_fine_e2e.py`
- **検証テスト**: `test_e2e_3episodes_sqlite`
- **実行コマンド**: `pytest tests/e2e/test_coarse_fine_e2e.py -k "test_e2e_3episodes_sqlite"`

### Step 27: 伏線回収の連動確認
- **目的**: 骨子で計画された伏線（`foreshadowing_plan`）が、JIT展開されたビートに反映され、執筆後の `ForeshadowingService` で回収検知されるかテスト。
- **対象ファイル**: `tests/e2e/test_coarse_fine_e2e.py`
- **検証テスト**: `test_e2e_foreshadowing_continuity`
- **実行コマンド**: `pytest tests/e2e/test_coarse_fine_e2e.py -k "test_e2e_foreshadowing_continuity"`

### Step 28: クリフハンガー連動確認
- **目的**: 骨子の `next_hook` が最終シーン（`scene_hook`）の展開に忠実に引き継がれ、本文末尾に反映されることを検証。
- **対象ファイル**: `tests/e2e/test_coarse_fine_e2e.py`
- **検証テスト**: `test_e2e_cliffhanger_reflection`
- **実行コマンド**: `pytest tests/e2e/test_coarse_fine_e2e.py -k "test_e2e_cliffhanger_reflection"`

### Step 29: プロセ精練（Prose Refiner）および局所パッチとの協調
- **目的**: 二段階化プロットから生成された本文が、既存の `UnifiedAuditor` 定量監査で 70点以上 を獲得することを確認。
- **対象ファイル**: `tests/e2e/test_coarse_fine_e2e.py`
- **検証テスト**: `test_e2e_audit_score_pass`
- **実行コマンド**: `pytest tests/e2e/test_coarse_fine_e2e.py -k "test_e2e_audit_score_pass"`

### Step 30: `Part 5` E2E テスト通過確認
- **目的**: E2E シミュレーションテストの全件通過確認。
- **実行コマンド**: `pytest tests/e2e/test_coarse_fine_e2e.py`

---

## Part 6: 全体リグレッション検証とドキュメント同期 (Step 31-36)

### Step 31: 既存プロット関連ユニットテスト全件パス検証
- **目的**: `tests/unit/models/test_plot.py` や `tests/unit/agents/test_plot.py` 等の既存テストが一切壊れていないことを確認。
- **実行コマンド**: `pytest tests/unit/models/ tests/unit/agents/ -k "plot"`

### Step 32: 既存執筆関連ユニットテスト全件パス検証
- **目的**: `tests/unit/agents/writing/` の全テストがパスすることを確認。
- **実行コマンド**: `pytest tests/unit/agents/writing/`

### Step 33: 既存EasyMode・パイプラインテスト全件パス検証
- **目的**: `tests/unit/easy_mode/` および `tests/unit/pipeline/` が 100% PASS することを確認。
- **実行コマンド**: `pytest tests/unit/easy_mode/ tests/unit/pipeline/`

### Step 34: 静的コード解析 (Ruff & Mypy) の実行
- **目的**: コードフォーマット・リント・型安全性の完全準拠を確認。
- **実行コマンド**: `ruff check src/ prompts/ && mypy src/services/default_plot_expander.py src/services/pipeline_steps.py`

### Step 35: `PHASE_ROADMAP_MASTER.md` および README の更新
- **目的**: 二段階化パイプライン（Coarse-to-Fine Expansion）が正式導入されたことをロードマップに記録。
- **対象ファイル**: `plans/PHASE_ROADMAP_MASTER.md`, `README.md`
- **変更内容**: 実装ステータス表に Phase J（Coarse-to-Fine プロット展開）の完了を反映。

### Step 36: J3 総合検証 ALL GREEN 確定
- **目的**: J1〜J3 で追加・改修された全テストを含む総合テストを実行し、完全なグリーンを確認。
- **実行コマンド**: `pytest tests/unit/models/test_plot_coarse_fine.py tests/unit/services/test_coarse_fine_expander.py tests/unit/pipeline/test_plan_step_coarse_fine.py tests/e2e/test_coarse_fine_e2e.py`
