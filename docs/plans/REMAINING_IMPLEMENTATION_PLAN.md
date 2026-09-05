# ⚠️ DEPRECATED (2026-09-04)

このドキュメントは **完了済み** です。実装の現状は以下を参照：

- **コード**: `src/backend/workflows/{full,easy_mode}_workflow.py` (両方とも `AutoWorkflowPipeline` に委譲済み)
- **テスト**: `tests/test_unified_pipeline.py` (26 テスト) / `tests/test_easy_mode_workflow.py` (7 テスト) / `tests/test_full_auto_workflow.py` (5 テスト)
- **実装計画**: `STEP_PLAN_DETAILED.md` (Step A-J すべて完了)
- **統合計画書**: `PIPELINE_UNIFICATION_PLAN.md` (ステータス: 完了)

このファイルは履歴保存のため残されています。新規実装は `STEP_PLAN_DETAILED.md` を参照してください。

---

# 残りの実装計画（Phase 3-4 統合パイプライン）

現在の状況に基づき、UNIFIED_PIPELINE_IMPLEMENTATION_PLAN.md の 36 ステップのうち、未完了または不完全なステップを抜粋・再編しました。

## フェーズ B: 進捗コールバックアダプタ実装 (Steps 6-9)

### Step 9: `AutoWorkflowPipeline.execute()` でアダプタを使用するよう修正
- **対象**: `src/services/auto_workflow_pipeline.py` の `execute` メソッド
- **現在**: `reporter` をそのまま各ステップに渡している
- **必要修正**: ワークフロー側で `ProgressReporterAdapter` を生成し、それを `execute` に渡す
- **ワークフロー側の修正**:
  - `full_auto_workflow.py`: `execute` 内で `adapter = ProgressReporterAdapter(reporter, is_easy_mode=False)` を生成し、`pipeline.execute(ctx, self.engine, adapter)` を呼び出す
  - `easy_mode_workflow.py`: 同様に `adapter = ProgressReporterAdapter(reporter, is_easy_mode=True)` を生成
- **確認**: 両ワークフローで進捗表示が正常動作すること

## フェーズ C: FullAutoWorkflow → 統合パイプライン委譲 (Steps 10-16)

### Step 10: `full_auto_workflow.py` の import 追加
- `from src.services.pipeline_param_mapper import map_fullauto_kwargs_to_context, map_context_to_fullauto_result`
- `from src.services.progress_reporter import ProgressReporterAdapter`

### Step 11: `execute()` 内で kwargs → Context 変換
- インラインマッピングを削除し、`ctx = map_fullauto_kwargs_to_context(kwargs)` に置き換える

### Step 12: パイプライン構築（既存コード流用・確認のみ）
- 変更不要（既に `create_full_auto_pipeline` を使用中）

### Step 13: 進捗アダプタ生成・実行
- `adapter = ProgressReporterAdapter(reporter, is_easy_mode=False)`
- `result = await pipeline.execute(ctx, self.engine, adapter)`

### Step 14: 結果を既存インターフェース dict に変換
- インライン変換を削除し、`return map_context_to_fullauto_result(ctx, result)` に置き換える

### Step 15: 旧ロジック（コメントアウトされていれば削除、なければ何もしない）
- `full_auto_workflow.py` 冲に旧実装残骸があれば削除
- なければスキップ

### Step 16: 既存 FullAutoWorkflow テスト実行・修正
- `pytest tests/ -k "full_auto" -v` を実行
- 失敗テストがあればマッピング関数またはアダプタを修正
- 全テストパスまで繰り返し

## フェーズ D: EasyModeWorkflow → 統合パイプライン委譲 (Steps 17-23)

### Step 17: `easy_mode_workflow.py` の import 追加
- `from src.services.pipeline_param_mapper import map_easymode_kwargs_to_context, map_context_to_easymode_result`
- `from src.services.progress_reporter import ProgressReporterAdapter`

### Step 18: `execute()` 内で kwargs → Context 変換
- インラインマッピングを削除し、`ctx = map_easymode_kwargs_to_context({ ... })` に置き換える

### Step 19: パイプライン構築
- 変更不要（既に `create_easy_mode_pipeline` を使用中）

### Step 20: 進捗アダプタ生成・実行
- `adapter = ProgressReporterAdapter(reporter, is_easy_mode=True)`
- `result = await pipeline.execute(ctx, self.engine, adapter)`

### Step 21: 結果を既存インターフェース dict に変換
- インライン変換を削除し、`return map_context_to_easymode_result(ctx, result)` に置き換える

### Step 22: 旧ロジック削除（残骸があれば）
- `easy_mode_workflow.py` 冲に旧実装残骸があれば削除

### Step 23: 既存 EasyModeWorkflow テスト実行・修正
- `pytest tests/ -k "easy_mode" -v` を実行
- 失敗あればマッピング/アダプタを修正
- 全テストパスまで繰り返し

## フェーズ E: API/CLI 動作確認・フィーチャーフラグ (Steps 24-30)

### Step 24: 環境変数 `USE_UNIFIED_PIPELINE` で新旧切替実装
- `src/backend/workflows/full_auto_workflow.py` と `easy_mode_workflow.py` の冒頭で：
  ```python
  import os
  USE_UNIFIED = os.getenv("USE_UNIFIED_PIPELINE", "1") == "1"
  ```
- `USE_UNIFIED=False` 時は旧ロジックを使用（またはエラーにする）。まずは `True` 固定で動作確認、後でフラグ化。
- **確認**: 環境変数で挙動切替可能

### Step 25-30: 手動テスト
- API および CLI の手動テストを実施し、動作を確認する
- （詳細については UNIFIED_PIPELINE_IMPLEMENTATION_PLAN.md を参照）

## フェーズ F: 旧コード削除・最終検証 (Steps 31-36)

### Step 31: 全テストスイート実行
- `pytest tests/ -v --tb=short` を実行
- 失敗テストを全て修正
- 目標: **0 failures**

### Step 32: `EasyModePipeline` 旧実装削除
- 削除対象: `src/easy_mode/pipeline.py`
- `src/easy_mode/__init__.py` から import 削除（必要に応じて）
- `grep -r "EasyModePipeline" src/ --include="*.py"` で参照残っていないこと確認

### Step 33: 未使用 import・デッドコード最終掃除
- `ruff check src/` で未使用 import 検出・削除
- `mypy src/` で型エラー修正
- 不要になった定数・ヘルパー関数削除

### Step 34: エンドツーエンド統合テスト（実環境）
- Docker Compose 本番相当環境で起動し、基本的なフローをテスト
- （時間がない場合は、ユニットテストがパスしていることを確認）

### Step 35: ドキュメント更新・完了記録
- `AGENTS.md` / `CLAUDE.md` 等のアーキテクチャ文書更新
- `CHANGELOG.md` に統合完了を記録
- `PIPELINE_UNIFICATION_PLAN.md` に完了マーク付与

## 注意事項
- 各ステップは 1 ファイル / 1 関数 / 1 クラス の変更のみに留める
- 1 ステップ完了ごとに動作確認コマンドを実行し、成功してから次へ進む
- 失敗したら前のステップに戻り、修正してから再試行