# AutoNovel 実装計画書: Phase J2
# プロット二段階化 (Coarse-to-Fine) - JIT Expander サービスの実装 (36 Steps)

**目的**: `EpisodeMacroSkeleton` を執筆直前にオンデマンド展開（Just-In-Time Expansion）するサービスを `src/services/default_plot_expander.py` に実装し、執筆パイプライン（`EpisodeWriter` / `WritingCoordinator`）と結合する。  
**デメリット対策の織り込み**:
1. **レイテンシ対策**: 小型高速モデルの割り当て（Model Tiering: `purpose="fast_expansion"`）
2. **直列待ち時間対策**: 非同期投機的プリフェッチ（パイプライン・インターリーブ）
3. **状態管理対策**: 冪等なオンデマンド・リゾルバ（`ensure_detailed_plot`）

---

## 📋 全体構成（36ステップ）

- **Part 1 (Step 1-6)**: `expand_macro_skeletons()`（骨子バッチ生成）の実装と単体検証
- **Part 2 (Step 7-12)**: `expand_single_micro()`（JIT微視的展開）と小型高速モデル連携
- **Part 3 (Step 13-18)**: 冪等オンデマンド・リゾルバ `ensure_detailed_plot()` の実装
- **Part 4 (Step 19-24)**: 非同期投機的プリフェッチ機構の実装（レイテンシ隠蔽）
- **Part 5 (Step 25-30)**: `WritingCoordinator` / `EpisodeWriter` 執筆直前フックの結合
- **Part 6 (Step 31-36)**: 障害復旧・リトライ耐性・状態遷移のテストと J2 総合検証

---

## Part 1: `expand_macro_skeletons()` の実装 (Step 1-6)

### Step 1: テストファイルの作成 `tests/unit/services/test_coarse_fine_expander.py`
- **目的**: JIT Expander 用の単体テストファイルを作成。
- **対象ファイル**: `tests/unit/services/test_coarse_fine_expander.py` (新規作成)
- **変更内容**: `pytest` によるモックLLMおよびリポジトリを使用したテストクラス `TestMacroExpander` を作成。
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py`

### Step 2: `DefaultPlotExpander.expand_macro_skeletons` メソッドのシグネチャ追加
- **目的**: 複数話の大局骨子を一括生成するメソッドの定義。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**:
  ```python
  async def expand_macro_skeletons(
      self,
      book_id: int,
      target_ep_list: list[int],
      reporter: IReporter | None = None,
      branch_id: int | None = None,
  ) -> list[EpisodeMacroSkeleton]:
  ```
- **検証テスト**: `test_expand_macro_skeletons_signature`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_macro_skeletons_signature"`

### Step 3: バイブル取得とプロンプト構築の結合
- **目的**: リポジトリから `bible` を取得し、`pm.build_macro_plot_skeleton_prompt` を呼び出す処理を実装。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: バイブル未存在時の安全な空リスト返却ガードを含む実装。
- **検証テスト**: `test_expand_macro_skeletons_bible_fetch`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_macro_skeletons_bible_fetch"`

### Step 4: LLM `generate_json` による `PlotMacroBatch` の呼び出し
- **目的**: `MODEL_PLANNING`（高品質標準モデル）を用いて `PlotMacroBatch` を生成・パース。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: `response_schema=PlotMacroBatch` を指定した呼び出しとエラーハンドリング。
- **検証テスト**: `test_expand_macro_skeletons_llm_call`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_macro_skeletons_llm_call"`

### Step 5: 生成された骨子（Skeleton）のDB一時保存
- **目的**: 各話の骨子をリポジトリ経由でDB（`plot` テーブル）に保存。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: `repo.save_macro_skeleton(book_id, ep.ep_num, ep)` の呼び出し。
- **検証テスト**: `test_expand_macro_skeletons_db_save`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_macro_skeletons_db_save"`

### Step 6: `Part 1` 単体テスト通過確認
- **目的**: 骨子一括生成ロジックのテスト全件通過。
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "TestMacroExpander"`

---

## Part 2: `expand_single_micro()` と小型高速モデル連携 (Step 7-12)

### Step 7: `expand_single_micro` メソッドのシグネチャ定義
- **目的**: 単一話の詳細ビート（3シーン×beats）をオンデマンド展開するメソッドを追加。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**:
  ```python
  async def expand_single_micro(
      self,
      book_id: int,
      ep_num: int,
      skeleton: EpisodeMacroSkeleton,
      previous_ending_text: str = "",
      reporter: IReporter | None = None,
      branch_id: int | None = None,
  ) -> PlotMicroBlueprint:
  ```
- **検証テスト**: `test_expand_single_micro_signature`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_single_micro_signature"`

### Step 8: 【デメリット1対策】小型高速モデル（`MODEL_FAST_EXPANSION`）の定義
- **目的**: 肉付け展開に特化した低レイテンシ・低コストモデル定数を定義。
- **対象ファイル**: `config/constants.py`
- **変更内容**: `MODEL_FAST_EXPANSION = "gemini-1.5-flash"` (または環境変数 `MODEL_FAST_EXPANSION` の取得) を追加。
- **検証テスト**: `test_constants_model_fast_expansion`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_constants_model_fast_expansion"`

### Step 9: 前話本文末尾テキスト（生文）の抽出・安全トリミング
- **目的**: 直前話の本文から末尾500文字を安全に抽出し、プロンプトに渡す前処理を実装。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: `previous_ending_text[-500:].strip()` の切り出しロジック。
- **検証テスト**: `test_previous_text_trimming`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_previous_text_trimming"`

### Step 10: `expand_single_micro` のプロンプト生成とLLM呼び出し
- **目的**: `pm.build_micro_scene_expander_prompt` を呼び出し、`MODEL_FAST_EXPANSION` で `PlotMicroBlueprint` を取得。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: `response_schema=PlotMicroBlueprint` を指定した高速生成。
- **検証テスト**: `test_expand_single_micro_llm_generation`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_single_micro_llm_generation"`

### Step 11: 骨子と肉付けのマージと `PlotEpisode` 構築
- **目的**: `merge_macro_and_micro(skeleton, micro_blueprint)` を実行し、完全な `PlotEpisode` を返す。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: マージ関数の呼び出しと整合性チェック。
- **検証テスト**: `test_expand_single_micro_merge`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_single_micro_merge"`

### Step 12: `Part 2` 単体テスト通過確認
- **目的**: 単一話JIT展開ロジックのテスト全件通過。
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_expand_single_micro"`

---

## Part 3: 冪等オンデマンド・リゾルバ `ensure_detailed_plot()` (Step 13-18)

### Step 13: 【デメリット3対策】`ensure_detailed_plot` の基本シグネチャ
- **目的**: 「既に詳細プロットがあれば即座に返し、無ければJIT展開する」完全冪等リゾルバを実装。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**:
  ```python
  async def ensure_detailed_plot(
      self,
      book_id: int,
      ep_num: int,
      branch_id: int = 1,
      reporter: IReporter | None = None,
  ) -> PlotEpisode:
  ```
- **検証テスト**: `test_ensure_detailed_plot_signature`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_ensure_detailed_plot_signature"`

### Step 14: 既存詳細プロットのキャッシュヒット判定
- **目的**: `plot.scenes` が3件以上存在する場合はLLMを一切呼ばずに即リターンする高速パスを実装。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: `if existing and hasattr(existing, "scenes") and len(existing.scenes) >= 3: return existing`
- **検証テスト**: `test_ensure_detailed_plot_cache_hit`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_ensure_detailed_plot_cache_hit"`

### Step 15: 骨子未存在時の自動フォールバック生成
- **目的**: 万一DBに骨子すら存在しない場合、自動的に `expand_macro_skeletons` を呼んで自己修復する。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_ensure_detailed_plot_missing_skeleton_fallback`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_ensure_detailed_plot_missing_skeleton_fallback"`

### Step 16: 直前話の本文自動取得
- **目的**: `repo.get_chapter(book_id, ep_num - 1)` から前話本文を自動ロード。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_ensure_detailed_plot_fetch_prev_chapter`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_ensure_detailed_plot_fetch_prev_chapter"`

### Step 17: 詳細プロットのDB Atomic更新
- **目的**: 展開された `PlotEpisode` をDBにコミットし、次回以降のキャッシュを有効化。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: `repo.save_plot(book_id, ep_num, merged_plot, branch_id=branch_id)`
- **検証テスト**: `test_ensure_detailed_plot_db_persist`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_ensure_detailed_plot_db_persist"`

### Step 18: `Part 3` 冪等性テスト通過確認
- **目的**: 2回連続で `ensure_detailed_plot` を呼んだ際、2回目のLLM呼び出し回数が 0 であることを検証。
- **検証テスト**: `test_ensure_detailed_plot_idempotency`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_ensure_detailed_plot_idempotency"`

---

## Part 4: 投機的プリフェッチ機構の実装 (Step 19-24)

### Step 19: 【デメリット2対策】非同期プリフェッチキューの設計
- **目的**: 執筆中に裏で次話の詳細ビートを展開しておくタスクマネージャーを設計。
- **対象ファイル**: `src/services/rag_prefetch_service.py` または `src/services/default_plot_expander.py`
- **変更内容**: `prefetch_next_episode_plot(book_id: int, next_ep: int, ...)` の非同期タスク生成。
- **検証テスト**: `test_prefetch_task_creation`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_prefetch_task_creation"`

### Step 20: 投機的コンテキスト（予定クリフハンガー）の抽出
- **目的**: 前話の本文が未完成の段階では、前話骨子の `next_hook.description` を仮の末尾テキストとして使用する。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_speculative_context_fallback`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_speculative_context_fallback"`

### Step 21: `asyncio.create_task` によるバックグラウンド実行
- **目的**: メインスレッド（本文執筆）をブロックせずにバックグラウンドで肉付け展開を実行。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_background_prefetch_nonblocking`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_background_prefetch_nonblocking"`

### Step 22: プリフェッチ結果のキャッシュ登録
- **目的**: 生成が完了したプリフェッチプロットをメモリまたはDBに事前格納。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_prefetch_cache_registration`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_prefetch_cache_registration"`

### Step 23: プリフェッチ失敗時のグレースフルフォールバック
- **目的**: バックグラウンドタスクが例外終了してもメイン執筆をクラッシュさせず、執筆直前に通常同期展開に切り替える。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_prefetch_failure_graceful_fallback`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_prefetch_failure_graceful_fallback"`

### Step 24: `Part 4` プリフェッチテスト通過確認
- **目的**: プリフェッチ機構の全件通過確認。
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "prefetch"`

---

## Part 5: `WritingCoordinator` / `EpisodeWriter` 結合 (Step 25-30)

### Step 25: `EpisodeWriter` のプロット取得箇所の特定
- **目的**: `src/agents/writing/episode_writer.py` におけるプロット参照箇所を調査・確認。
- **対象ファイル**: `src/agents/writing/episode_writer.py`
- **検証テスト**: 既存テスト `tests/unit/agents/writing/test_episode_writer.py` の動作確認

### Step 26: `EpisodeWriter.write_beat_to_scene` の直前に `ensure_detailed_plot` フックを挿入
- **目的**: 本文執筆の直前に必ず詳細プロットが展開されている状態を保証。
- **対象ファイル**: `src/agents/writing/episode_writer.py`
- **変更内容**:
  ```python
  if self.plot_expander and hasattr(self.plot_expander, "ensure_detailed_plot"):
      plot = await self.plot_expander.ensure_detailed_plot(book_id, ep_num, branch_id=branch_id)
      context["plot"] = plot
  ```
- **検証テスト**: `tests/unit/agents/writing/test_episode_writer.py::test_writer_with_jit_plot`
- **実行コマンド**: `pytest tests/unit/agents/writing/test_episode_writer.py -k "test_writer_with_jit_plot"`

### Step 27: 次話プリフェッチトリガーの配置
- **目的**: 第N話の本文保存（`save_chapter`）直後に、非同期で第N+1話のプリフェッチをキック。
- **対象ファイル**: `src/agents/writing/episode_writer.py` または `src/domain/writing/coordinator.py`
- **変更内容**: `self.plot_expander.prefetch_next_episode_plot(book_id, ep_num + 1)`
- **検証テスト**: `test_writer_triggers_prefetch`
- **実行コマンド**: `pytest tests/unit/agents/writing/test_episode_writer.py -k "test_writer_triggers_prefetch"`

### Step 28: `WritingCoordinator` のエピソード生成ループへの適応
- **目的**: `WritingCoordinator.generate_episodes` におけるプロット事前チェックの緩和。
- **対象ファイル**: `src/domain/writing/coordinator.py`
- **変更内容**: 全話一括展開を待たず、骨子のみで執筆ループに入射できるようにガードを更新。
- **検証テスト**: `tests/unit/domain/writing/test_coordinator.py`
- **実行コマンド**: `pytest tests/unit/domain/writing/test_coordinator.py`

### Step 29: レポーター（進捗UI）へのJIT展開メッセージ通知
- **目的**: ユーザーに進捗が分かるよう「第N話の詳細ビートを展開中...」のステータス報告を追加。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **変更内容**: `reporter.report(f"Ep.{ep_num}: 詳細演出ビートを展開中...", "info")`
- **検証テスト**: `test_reporter_progress_on_jit`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_reporter_progress_on_jit"`

### Step 30: `Part 5` 執筆連携テスト通過確認
- **目的**: 執筆エージェントとの結合テスト全件通過。
- **実行コマンド**: `pytest tests/unit/agents/writing/test_episode_writer.py tests/unit/domain/writing/test_coordinator.py`

---

## Part 6: 障害復旧・リトライ耐性と J2 総合検証 (Step 31-36)

### Step 31: LLMパースエラー時のフォールバックテスト
- **目的**: JIT展開時にLLMが不正なJSONを返した場合、骨子の `inciting_event` / `climax_payoff` から安全な最小ビートを自動構成することを確認。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_jit_expansion_llm_json_error_fallback`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_jit_expansion_llm_json_error_fallback"`

### Step 32: ネットワークタイムアウト時のリトライ動作テスト
- **目的**: JIT展開のタイムアウト時に最大2回までリトライが実行されることを検証。
- **対象ファイル**: `src/services/default_plot_expander.py`
- **検証テスト**: `test_jit_expansion_timeout_retry`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_jit_expansion_timeout_retry"`

### Step 33: 中断再開（Resume）時の整合性テスト
- **目的**: 第1〜2話執筆後にプロセスが強制終了し再開した場合、第1〜2話のビート再展開がスキップされ第3話から再開することを検証。
- **対象ファイル**: `tests/unit/services/test_coarse_fine_expander.py`
- **検証テスト**: `test_resume_from_interruption`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_resume_from_interruption"`

### Step 34: 複数話（3話連続）シミュレーションテスト
- **目的**: 第1話〜第3話まで、骨子バッチ生成 → JIT展開 → 執筆がシームレスに連動することをモックで検証。
- **検証テスト**: `test_three_episodes_coarse_fine_simulation`
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py -k "test_three_episodes_coarse_fine_simulation"`

### Step 35: 型チェック (mypy) の通過確認
- **目的**: J2 で変更・追加した全コードの型整合性を検証。
- **実行コマンド**: `mypy src/services/default_plot_expander.py src/agents/writing/episode_writer.py`

### Step 36: J2 総合テストスイート ALL GREEN 確認
- **目的**: Part 1〜6 の全テストが 100% PASS することを確認。
- **実行コマンド**: `pytest tests/unit/services/test_coarse_fine_expander.py tests/unit/agents/writing/test_episode_writer.py`
