# StreamingPlotScheduler 改善実装計画 (72ステップ)

## 概要
StreamingPlotScheduler (src/agents/writing_scheduler.py) の9つの改善を72の小さなステップに分割。

---

## 改善1: 待望時間トラッキングの修正 (ステップ 1-10)

### 現状の問題
- `PrefetchPolicy` の `record_wait_time()` がどこからも呼ばれていない
- `_wait_times` リストに何も入らないため `estimate_depth()` が常に `base_depth` を返す
- `_gen_start_times` もタスク完了時にクリーンアップされない

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 1 | `_wait_times` 使用箇所を削除 | writing_scheduler.py | 61 | `self._wait_times: List[float] = []` を削除 |
| 2 | `PrefetchPolicy.record_wait_time` 削除 | writing_scheduler.py | 23-26 | `PrefetchPolicy` から `record_wait_time` メソッドを削除 |
| 3 | `PrefetchPolicy.wait_times` 削除 | writing_scheduler.py | 16 | `self.wait_times: List[float] = []` を削除 |
| 4 | `estimate_depth()` を簡略化 | writing_scheduler.py | 28-34 | `wait_times` なし版に修正: `ratio` 計算を削除し `return self.base_depth` のみ |
| 5 | `PrefetchPolicy` クラスの削除 | writing_scheduler.py | 10-34 | `PrefetchPolicy` クラス全体を削除 |
| 6 | `self._prefetch_policy` 削除 | writing_scheduler.py | 63 | `self._prefetch_policy = PrefetchPolicy()` を削除 |
| 7 | `get_latencies()` の `wait_avg` 削除 | writing_scheduler.py | 193 | `wait_avg` 計算を削除し `gen_avg` のみ返す |
| 8 | インポート `List` が未使用か確認 | writing_scheduler.py | 3 | `List` が他で使われていないか確認 |
| 9 | 型ヒントの更新確認 | writing_scheduler.py | 61 | `_wait_times` 削除後の mypy チェック |
| 10 | テスト実行して動作確認 | - | - | `pytest tests/` を実行して既存機能動作確認 |

---

## 改善2: 依存関係（depends_on）実装 (ステップ 11-18)

### 現状の問題
- `depends_on` パラメータを受け取るが、実際に依存先に待機していない

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 11 | `await_plot_ready()` が返すものを確認 | writing_scheduler.py | 131-148 | 既存コード理解しコメント追加 |
| 12 | `depends_on` が自身のタスクにあるかチェック | writing_scheduler.py | 72-75 | 待機ロジックが既に存在するのを確認（実装済み） |
| 13 | コメント改善: 依存解決の流れを文書化 | writing_scheduler.py | 71-76 | `# Check dependency` コメントを詳細化 |
| 14 | 循環参照防止のテストケース追加 | tests/ | 新規 | `depends_on` が自身を指すケースのテスト |
| 15 | 存在しない Episode への依存テスト | tests/ | 新規 | `depends_on=999` のようなケースのテスト |
| 16 | 依存先がキャンセルされた時のテスト | tests/ | 新規 | `cancel_range()` 後の依存解決テスト |
| 17 | ドキュメント追加: depends_on 使用例 | docstring | 65 | `schedule_plot_generation` に使用例を追記 |
| 18 | テスト実行 | - | - | 新規テスト + 既存テスト実行 |

---

## 改善3: LLM生成へのタイムアウト導入 (ステップ 19-26)

### 現状の問題
- `expand_plots()` 呼び出しにタイムアウトがない
- LLM が応答しない場合永久にブロックする

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 19 | `asyncio` インポート確認 | writing_scheduler.py | 1 | `asyncio` がインポート済みか確認 |
| 20 | `DEFAULT_TIMEOUT` 定数追加 | writing_scheduler.py | 7付近 | `DEFAULT_TIMEOUT = 60  # seconds` 追加 |
| 21 | `__init__` に `timeout` パラメータ追加 | writing_scheduler.py | 40 | `timeout: int = DEFAULT_TIMEOUT` 追加 |
| 22 | `self._timeout` インスタンス変数保存 | writing_scheduler.py | 40-63 | `self._timeout = timeout` 保存 |
| 23 | `_run_gen` 内にタイムアウト適用 | writing_scheduler.py | 94 | `await asyncio.wait_for(self.planner.expand_plots(...), timeout=self._timeout)` |
| 24 | `asyncio.TimeoutError` キャッチ追加 | writing_scheduler.py | 118付近 | `except asyncio.TimeoutError:` 追加してタイムアウト処理 |
| 25 | タイムアウト時のレポーター出力追加 | writing_scheduler.py | 新規 | `self.reporter.report(f"⏱️ Ep.{ep_num} タイムアウト ({self._timeout}s)", "error")` |
| 26 | テスト: タイムアウト発生のモックテスト | tests/ | 新規 | LLM が時間内に返さない場合のテスト |

---

## 改善4: メモリリーク修正（_gen_start_times クリーンアップ）(ステップ 27-32)

### 現状の問題
- `_gen_start_times` はタスク作成時に追加されるが、完了時に削除されない
- 長期間稼働時にメモリリーク

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 27 | `_gen_start_times` 追加箇所確認 | writing_scheduler.py | 78 | `self._gen_start_times[ep_num] = ...` 箇所特定 |
| 28 | `_run_gen()` 完了時にクリーンアップ追加 | writing_scheduler.py | 121付近 | `_gen_start_times.pop(ep_num, None)` を finally ブロックで追加 |
| 29 | `try-finally` 構造で完了時必ずクリーンアップ | writing_scheduler.py | 80-127 | `_run_gen()` を `try-finally` で囲む |
| 30 | `cancel_range()` でもクリーンアップ | writing_scheduler.py | 175 | `task.cancel()` 前に `_gen_start_times.pop(ep_num, None)` |
| 31 | キャンセル時のクリーンアップ確認 | writing_scheduler.py | 122-123 | `CancelledError` 処理時もクリーンアップされるか確認 |
| 32 | メモリリーク修正確認テスト | tests/ | 新規 | 大量タスク作成/完了後の `_gen_start_times` サイズ確認 |

---

## 改善5: デッドコード削除（_try_generate）(ステップ 33-35)

### 現状の問題
- `_try_generate()` メソッド（159-169行）が定義済みだがどこからも呼ばれていない

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 33 | `_try_generate` が呼ばれていないか検索 | 全ファイル | - | `grep -r "_try_generate"` で全呼出箇所検索 |
| 34 | `_try_generate` メソッド削除 | writing_scheduler.py | 159-169 | 全文削除 |
| 35 | 削除後テスト実行 | - | - | `pytest tests/` で全テスト通過確認 |

---

## 改善6: 型ヒント修正（IPromptManager）(ステップ 36-40)

### 現状の問題
- `IPromptManager` が型の名前だけ使われ、インポートされていない

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 36 | `IPromptManager` の定義場所確認 | src/core/ | - | `grep -r "class IPromptManager"` で定義探索 |
| 37 | `IPromptManager` インポート追加 | writing_scheduler.py | 3-5 | `from src.core.interfaces import IPromptManager` 追加 |
| 38 | 文字列 `"IPromptManager"` を削除 | writing_scheduler.py | 39 | `pm: "IPromptManager"` → `pm: IPromptManager` |
| 39 | mypy チェック実行 | - | - | `mypy src/agents/writing_scheduler.py` 実行 |
| 40 | エラーがあれば修正 | - | - | mypy エラーに応じて修正 |

---

## 改善7: 优先级キューサポート (ステップ 41-52)

### 現状の問題
- 現在はFIFOのみ
- クライマックスEpisodeなど優先度の高いものを先に処理できない

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 41 | タスク優先度データ構造設計 | writing_scheduler.py | 新規 | `_task_priorities: Dict[int, int] = {}` 追加 (数字が小さい＝高優先度) |
| 42 | `__init__` に `_task_priorities` 初期化 | writing_scheduler.py | 63付近 | `self._task_priorities: Dict[int, int] = {}` 追加 |
| 43 | `schedule_plot_generation` に `priority` 追加 | writing_scheduler.py | 65 | `priority: int = 5` パラメータ追加 (デフォルト5) |
| 44 | `priority` を保存 | writing_scheduler.py | 77付近 | `self._task_priorities[ep_num] = priority` |
| 45 | `pending_episodes` を優先度順にソート | writing_scheduler.py | 186 | `sorted([ep for ep, t in self.tasks.items() if not t.done()], key=lambda ep: self._task_priorities.get(ep, 5))` |
| 46 | `get_next_episode` ヘルパー追加 | writing_scheduler.py | 新規 | 優先度最高的未完了Episodeを返すメソッド追加 |
| 47 | `cancel_range` で priority も削除 | writing_scheduler.py | 175 | `self._task_priorities.pop(ep_num, None)` 追加 |
| 48 | ドキュメント: priority パラメータ使用例 | writing_scheduler.py | 65 | docstring に使用例追加 |
| 49 | 優先度テスト: 高優先度が先に完了 | tests/ | 新規 | priority=1 と priority=10 のタスクを投入し確認 |
| 50 | 優先度テスト: キャンセル時の清理 | tests/ | 新規 | キャンセル後 priority が削除されるか確認 |
| 51 | 同優先度のFIFO動作確認 | tests/ | 新規 | 同一優先度で投入順に戻るか確認 |
| 52 | 全テスト実行 | - | - | `pytest tests/` 通過確認 |

---

## 改善8: サーキットブレーカー実装 (ステップ 53-62)

### 現状の問題
- 連続失敗時に無限リトライし続ける
- リソースの無駄遣い

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 53 | `__init__` にサーキットブレーカーパラメータ追加 | writing_scheduler.py | 40 | `circuit_breaker_threshold: int = 5` 追加 |
| 54 | `self._consecutive_errors` 初期化 | writing_scheduler.py | 63付近 | `self._consecutive_errors = 0` 追加 |
| 55 | `self._circuit_open` 初期化 | writing_scheduler.py | 63付近 | `self._circuit_open = False` 追加 |
| 56 | `_run_gen()` 开始前にサーキットチェック | writing_scheduler.py | 80付近 | `if self._circuit_open: raise RuntimeError("Circuit breaker open")` |
| 57 | 成功時に `_consecutive_errors` リセット | writing_scheduler.py | 103付近 | `self._consecutive_errors = 0` 追加 |
| 58 | エラー時に `_consecutive_errors` increament | writing_scheduler.py | 125付近 | `self._consecutive_errors += 1` 追加 |
| 59 | 閾値超過でサーキットオープン | writing_scheduler.py | 125付近 | `if self._consecutive_errors >= self._circuit_breaker_threshold: self._circuit_open = True` |
| 60 | サーキットオープンのレポーター出力 | writing_scheduler.py | 新規 | `self.reporter.report("🔴 サーキットブレーカーオープン", "error")` |
| 61 | `reset_circuit_breaker()` メソッド追加 | writing_scheduler.py | 新規 | 手動リセット用メソッド追加 |
| 62 | サーキットブレーカーテスト | tests/ | 新規 | 5回連続失敗後にサーキットが開くか確認 |

---

## 改善9: 進捗コールバック追加 (ステップ 63-72)

### 現状の問題
- 外部システム（UI）がタスク状態変化を購読できない

### ステップ

| # | ステップ | ファイル | 行 | 詳細 |
|---|---------|---------|-----|-------|
| 63 | `CallbackType` 型定義 | writing_scheduler.py | 新規 | `TaskState = Literal["scheduled", "running", "completed", "failed", "cancelled"]` |
| 64 | `TaskCallback = Callable[[int, TaskState], None]` | writing_scheduler.py | 新規 | コールバック型定義 |
| 65 | `__init__` に `_callbacks` 追加 | writing_scheduler.py | 63付近 | `self._callbacks: List[TaskCallback] = []` |
| 66 | `register_callback()` メソッド追加 | writing_scheduler.py | 新規 | コールバック登録メソッド追加 |
| 67 | `_emit_callback()` ヘルパー追加 | writing_scheduler.py | 新規 | 全コールバック呼び出しヘルパー追加 |
| 68 | タスクスケジュール時に "scheduled" コールバック | writing_scheduler.py | 77付近 | `_emit_callback(ep_num, "scheduled")` 追加 |
| 69 | タスク完了時に "completed" コールバック | writing_scheduler.py | 103付近 | `_emit_callback(ep_num, "completed")` 追加 |
| 70 | タスク失敗時に "failed" コールバック | writing_scheduler.py | 120付近 | `_emit_callback(ep_num, "failed")` 追加 |
| 71 | タスクキャンセル時に "cancelled" コールバック | writing_scheduler.py | 122付近 | `_emit_callback(ep_num, "cancelled")` 追加 |
| 72 | コールバックテスト | tests/ | 新規 | コールバックが正しく呼ばれるか確認 |

---

## テスト実行順序

```
# 改善1 (ステップ10): テスト
pytest tests/unit/test_writing_scheduler.py -v

# 改善2 (ステップ18): テスト
pytest tests/ -v -k "depend"

# 改善3 (ステップ26): テスト
pytest tests/ -v -k "timeout"

# 改善4 (ステップ32): テスト
pytest tests/ -v -k "memory"

# 改善5 (ステップ35): テスト
pytest tests/ -v

# 改善6 (ステップ40): mypy
mypy src/agents/writing_scheduler.py

# 改善7 (ステップ52): テスト
pytest tests/ -v -k "priority"

# 改善8 (ステップ62): テスト
pytest tests/ -v -k "circuit"

# 改善9 (ステップ72): テスト
pytest tests/ -v -k "callback"

# 全テスト実行
pytest tests/ -v
```

---

## ロールバック plan

各改善後、何か問題があれば以下でロールバック:

```bash
# 直前のコミットに戻る
git checkout HEAD~1 -- src/agents/writing_scheduler.py

# 特定改善前に戻る
git checkout <改善X開始前のコミット> -- src/agents/writing_scheduler.py
```

---

## 完了条件

- [ ] ステップ1-10: 待望時間トラッキング修正完了
- [ ] ステップ11-18: 依存関係実装完了
- [ ] ステップ19-26: タイムアウト導入完了
- [ ] ステップ27-32: メモリリーク修正完了
- [ ] ステップ33-35: デッドコード削除完了
- [ ] ステップ36-40: 型ヒント修正完了
- [ ] ステップ41-52: 优先级キューサポート完了
- [ ] ステップ53-62: サーキットブレーカー実装完了
- [ ] ステップ63-72: 進捗コールバック完了
- [ ] 全テスト通過
- [ ] mypy エラーなし