# 統合パイプライン 完全実装計画書（36ステップ詳細版）

**対象**: `PIPELINE_UNIFICATION_PLAN.md` の Phase 3-4 (Step 21-32) を **36の微小ステップ** に分解  
**目的**: 低性能LLMでも迷わず実装できる粒度まで分割  
**前提**: Phase 1-2 (Step 1-20) は完了済み、`AutoWorkflowPipeline` + 新Step群が動作可能

---

## 全体構成: 6フェーズ 36ステップ

| フェーズ | 目的 | ステップ数 |
|---------|------|-----------|
| Phase A | パラメータマッピングユーティリティ作成 | 1-5 |
| Phase B | 進捗コールバックアダプタ実装 | 6-9 |
| Phase C | FullAutoWorkflow → 統合パイプライン委譲 | 10-16 |
| Phase D | EasyModeWorkflow → 統合パイプライン委譲 | 17-23 |
| Phase E | API/CLI 動作確認・フィーチャーフラグ | 24-30 |
| Phase F | 旧コード削除・最終検証 | 31-36 |

---

## Phase A: パラメータマッピングユーティリティ作成 (Steps 1-5)

### Step 1: `src/services/pipeline_param_mapper.py` 新規作成（スケルトン）
```python
# ファイル作成のみ。関数シグネチャだけ定義。
def map_fullauto_kwargs_to_context(kwargs: dict) -> WorkflowContext: ...
def map_easymode_kwargs_to_context(kwargs: dict) -> WorkflowContext: ...
def map_context_to_fullauto_result(ctx: WorkflowContext, result: FullAutoWorkflowResult) -> dict: ...
def map_context_to_easymode_result(ctx: WorkflowContext, result: FullAutoWorkflowResult) -> dict: ...
```
**確認**: `python -c "from src.services.pipeline_param_mapper import map_fullauto_kwargs_to_context; print('OK')"`

---

### Step 2: FullAuto 用 kwargs → WorkflowContext 変換実装
**対象**: `map_fullauto_kwargs_to_context`
- 必須: `genre`, `keywords`, `archetype_key`, `target_eps`, `initial_limit`, `word_count`
- 任意: `concept`, `tone_vibe`, `user_prompt`, `illustration_settings`, `enable_spice_guard`
- 固定値: `enable_catharsis_analysis=True`, `enable_marketing=True`, `max_retries=1`, `is_easy_mode=False`
- `preset_name` は空文字でOK
**確認**: 単体テストで全フィールドが正しくマッピングされること

---

### Step 3: EasyMode 用 kwargs → WorkflowContext 変換実装
**対象**: `map_easymode_kwargs_to_context`
- 引数: `genre`, `keywords(list)`, `protagonist_type`, `target_episodes`, `words_per_episode`, `enable_audit`, `max_rewrites`, `**kwargs`
- マッピング:
  - `keywords` → `", ".join(keywords)`
  - `protagonist_type` → `archetype_key`
  - `target_episodes` → `target_eps`
  - `words_per_episode` → `word_count`
  - `enable_audit` → `enable_spice_guard`
  - `max_rewrites` → `max_rewrite_iterations`
  - 固定: `target_audit_score=95.0`, `enable_illustration=False`, `enable_catharsis_analysis=False`, `enable_marketing=True`, `max_retries=0`, `is_easy_mode=True`
  - `preset_name` = `kwargs.get("preset_name", "")`
**確認**: 単体テストで全フィールド正しくマッピング

---

### Step 4: Context → FullAuto 結果 dict 変換実装
**対象**: `map_context_to_fullauto_result`
- 返却キー: `book_id`, `title`, `chars_count`, `failed_episodes`, `zip_data`, `zip_filename`, `illustrations`, `status`, `easy_parameters`, `average_audit_score`, `episodes_detail`
- `zip_data` は `ctx.zip_data`、`zip_filename` は `ctx.zip_filename`
- `easy_parameters` は `ctx.easy_parameters`
**確認**: 単体テストで dict 形式が既存インターフェースと一致

---

### Step 5: Context → EasyMode 結果 dict 変換実装
**対象**: `map_context_to_easymode_result`
- 返却キー: `title`, `concept`, `total_episodes`, `total_words`, `average_audit_score`, `genre`, `episodes`, `status`
- `episodes`: `ctx.episodes_detail` から `{episode_num, title, word_count, audit_score, audit_passed, rewrite_count, needs_human_review}` を抽出
- `total_words` = `ctx.chars_count`
- `title` = `ctx.title` または `ctx.easy_parameters.get("title", "")`
- `concept` = `ctx.easy_parameters.get("concept", "")`
**確認**: 単体テストで dict 形式が既存インターフェースと一致

---

## Phase B: 進捗コールバックアダプタ実装 (Steps 6-9)

### Step 6: `src/services/progress_reporter.py` に `ProgressReporterAdapter` クラス追加
```python
class ProgressReporterAdapter:
    """FullAuto(reporter.update_progress) と EasyMode(callback) を統一"""
    def __init__(self, reporter: StatusReporter, is_easy_mode: bool):
        self.reporter = reporter
        self.is_easy_mode = is_easy_mode
    def report(self, step: int, total: int, msg: str = "", sub_msg: str = ""): ...
    def update_progress(self, current: int, total: int, message: str = "", sub_message: str = ""): ...
```
**確認**: クラス定義のみで import エラーなし

---

### Step 7: FullAuto モード進捗アダプタ実装
- `update_progress(step, total, msg, sub_msg)` をそのまま `reporter.update_progress` に転送
- `report(step, total, msg, sub_msg)` も同様
**確認**: `reporter.update_progress` が呼ばれること

---

### Step 8: EasyMode モード進捗アダプタ実装
- 内部ステージ名 → メッセージ変換テーブル保持（bible, plot, writing, episode_complete, finalizing）
- `report(step, total, msg, sub_msg)` で stage 推定し `callback(stage, current, total)` 形式で呼び出し
- `update_progress` は `report` に委譲
**確認**: 既存 `callback(stage, current, total)` 形式で進捗通知されること

---

### Step 9: `AutoWorkflowPipeline.execute()` でアダプタ使用するよう修正
- `execute()` 内で `ProgressReporterAdapter(reporter, ctx.is_easy_mode)` 生成
- 各 Step 呼び出し時に `reporter` 代わりにアダプタを渡す（Step 側は `reporter.update_progress` / `reporter.report` 使用継続）
- 互換性のため `reporter` もそのまま渡す（Step が直接使う場合もあるため）
**確認**: 両ワークフローで進捗表示が正常動作

---

## Phase C: FullAutoWorkflow → 統合パイプライン委譲 (Steps 10-16)

### Step 10: `full_auto_workflow.py` の import 追加
```python
from src.services.pipeline_param_mapper import (
    map_fullauto_kwargs_to_context,
    map_context_to_fullauto_result,
)
from src.services.progress_reporter import ProgressReporterAdapter
```
**確認**: import エラーなし

---

### Step 11: `execute()` 内で kwargs → Context 変換
```python
ctx = map_fullauto_kwargs_to_context(kwargs)
```
**確認**: `ctx` に全フィールドが正しく入ること

---

### Step 12: パイプライン構築（既存コード流用・確認のみ）
```python
pipeline = create_full_auto_pipeline(
    enable_spice_guard=ctx.enable_spice_guard,
    enable_illustration=ctx.enable_illustration,
    enable_catharsis_analysis=ctx.enable_catharsis_analysis,
    enable_marketing=ctx.enable_marketing,
    max_retries=ctx.max_retries,
)
```
**確認**: 既存と同等のパイプラインが構築されること

---

### Step 13: 進捗アダプタ生成・実行
```python
adapter = ProgressReporterAdapter(reporter, is_easy_mode=False)
result = await pipeline.execute(ctx, self.engine, adapter)
```
**確認**: パイプライン実行が完了し `FullAutoWorkflowResult` が返る

---

### Step 14: 結果を既存インターフェース dict に変換
```python
return map_context_to_fullauto_result(ctx, result)
```
**確認**: 返却 dict が既存テストの期待値と一致

---

### Step 15: 旧ロジック（コメントアウトされていれば削除、なければ何もしない）
- `full_auto_workflow.py` 内に旧実装残骸があれば削除
- なければスキップ
**確認**: ファイル内に統合パイプライン呼び出しのみ残る

---

### Step 16: 既存 FullAutoWorkflow テスト実行・修正
```bash
pytest tests/ -k "full_auto" -v
```
- 失敗テストがあればマッピング関数またはアダプタを修正
- 全テストパスまで繰り返し
**確認**: 0 failures

---

## Phase D: EasyModeWorkflow → 統合パイプライン委譲 (Steps 17-23)

### Step 17: `easy_mode_workflow.py` の import 追加
```python
from src.services.pipeline_param_mapper import (
    map_easymode_kwargs_to_context,
    map_context_to_easymode_result,
)
from src.services.progress_reporter import ProgressReporterAdapter
```
**確認**: import エラーなし

---

### Step 18: `execute()` 内で kwargs → Context 変換
```python
ctx = map_easymode_kwargs_to_context({
    "genre": genre,
    "keywords": keywords,
    "protagonist_type": protagonist_type,
    "target_episodes": target_episodes,
    "words_per_episode": words_per_episode,
    "enable_audit": enable_audit,
    "max_rewrites": max_rewrites,
    **kwargs,
})
```
**確認**: `ctx` に全フィールド正しく入る

---

### Step 19: パイプライン構築
```python
pipeline = create_easy_mode_pipeline(
    genre=genre,
    target_episodes=target_episodes,
    enable_spice_guard=enable_audit,
    max_rewrite_iterations=max_rewrites,
    target_audit_score=95.0,
    enable_marketing=True,
)
```
**確認**: 既存と同等のパイプライン構築

---

### Step 20: 進捗アダプタ生成・実行
```python
adapter = ProgressReporterAdapter(reporter, is_easy_mode=True)
result = await pipeline.execute(ctx, self.engine, adapter)
```
**確認**: パイプライン実行完了

---

### Step 21: 結果を既存インターフェース dict に変換
```python
return map_context_to_easymode_result(ctx, result)
```
**確認**: 返却 dict が既存テスト期待値と一致

---

### Step 22: 旧ロジック削除（残骸があれば）
**確認**: ファイルが委譲のみになる

---

### Step 23: 既存 EasyModeWorkflow テスト実行・修正
```bash
pytest tests/ -k "easy_mode" -v
```
- 失敗あればマッピング/アダプタ修正
**確認**: 0 failures

---

## Phase E: API/CLI 動作確認・フィーチャーフラグ (Steps 24-30)

### Step 24: 環境変数 `USE_UNIFIED_PIPELINE` で新旧切替実装
- `src/backend/workflows/full_auto_workflow.py` と `easy_mode_workflow.py` の冒頭で：
```python
import os
USE_UNIFIED = os.getenv("USE_UNIFIED_PIPELINE", "1") == "1"
```
- `USE_UNIFIED=False` 時は旧ロジック（残しておくか、エラーにするか選択）
- まずは `True` 固定で動作確認、後でフラグ化
**確認**: 環境変数で挙動切替可能

---

### Step 25: `POST /api/full-auto/start` 手動テスト
```bash
curl -X POST http://localhost:8200/api/full-auto/start \
  -H "Content-Type: application/json" \
  -d '{"genre":"ファンタジー","keywords":"チート,無双","archetype_key":"王道ざまぁ（爽快感最大）","target_eps":3,"initial_limit":3,"word_count":2000,"concept":"テスト","tone_vibe":0.6}'
```
- タスクID返却 → ポーリングで完了確認
- 結果に `title`, `chars_count`, `status: "success"` 含まれること
**確認**: 手動で全フロー動作

---

### Step 26: `POST /api/easy-mode/start` 手動テスト（かんたんモード）
```bash
curl -X POST http://localhost:8200/api/easy-mode/start \
  -H "Content-Type: application/json" \
  -d '{"genre":"ファンタジー","keywords":["主人公","剣術"],"protagonist_type":"チート主人公","target_episodes":3,"words_per_episode":2000,"enable_audit":true,"max_rewrites":2}'
```
- 同様にポーリング→完了確認
- `episodes` 配列に3話分入ること
**確認**: 手動で全フロー動作

---

### Step 27: CLI エントリーポイント確認（full-auto）
```bash
python -m src.cli full-auto --genre ファンタジー --keywords "チート,無双" --archetype_key "王道ざまぁ" --target_eps 3 --word_count 2000
```
- 正常完了し結果表示されること
**確認**: CLI 正常動作

---

### Step 28: CLI エントリーポイント確認（easy-mode）
```bash
python -m src.cli easy-mode --genre ファンタジー --keywords 主人公,剣術 --protagonist_type チート主人公 --target_episodes 3 --words_per_episode 2000
```
**確認**: CLI 正常動作

---

### Step 29: キャンセル処理テスト
- 生成開始直後に `DELETE /api/full-auto/task/{task_id}` または `DELETE /api/easy-mode/task/{task_id}`
- ステータスが `cancelled` / `stopped` になること
- パイプライン内で `reporter.state.should_stop()` が効くこと
**確認**: 中断処理が正常動作

---

### Step 30: エラー伝播テスト
- 不正な API キー / 無効なジャンル / LLM タイムアウト等を意図的に発生
- パイプラインが `status: "failed"` または適切なエラーで返ること
- 例外が握りつぶされず上位まで伝播すること
**確認**: エラーハンドリング正常

---

## Phase F: 旧コード削除・最終検証 (Steps 31-36)

### Step 31: 全テストスイート実行
```bash
pytest tests/ -v --tb=short
```
- 失敗テストを全て修正（マッピング、アダプタ、パイプライン内部）
- 目標: **0 failures**
**確認**: 全テストパス

---

### Step 32: `FullAutoWorkflow` 旧実装ファイル削除
- 削除対象: `src/backend/workflows/full_auto_workflow.py`
- `src/backend/workflows/__init__.py` から import 削除、`WORKFLOW_REGISTRY` から削除
- `grep -r "FullAutoWorkflow" src/ --include="*.py"` で参照残っていないこと確認
**確認**: 参照ゼロ

---

### Step 33: `EasyModePipeline` 旧実装削除
- 削除対象:
  - `src/easy_mode/pipeline.py`
  - `src/easy_mode/spice_guard.py` （adapter に移植済みなら）
  - `src/easy_mode/__init__.py` （空なら削除、他に export あれば残す）
  - `src/backend/workflows/easy_mode_workflow.py`
- `grep -r "EasyModePipeline\|EasyModeWorkflow" src/ --include="*.py"` で参照ゼロ確認
**確認**: 参照ゼロ

---

### Step 34: 未使用 import・デッドコード最終掃除
- `ruff check src/` で未使用 import 検出・削除
- `mypy src/` で型エラー修正
- 不要になった定数・ヘルパー関数削除
**確認**: lint/typecheck 0 errors

---

### Step 35: エンドツーエンド統合テスト（実環境）
- Docker Compose 本番相当環境で起動
- 以下シナリオ実行：
  1. 全自動モードで 3話生成 → ZIP 出力確認
  2. かんたんモードで 3話生成 → ZIP 出力確認
  3. 上級者 Studio で GraphRAG 表示確認
  4. 中断・リトライ動作確認
**確認**: 全シナリオパス

---

### Step 36: ドキュメント更新・完了記録
- `AGENTS.md` / `CLAUDE.md` 等のアーキテクチャ文書更新（統合パイプライン完成版）
- `CHANGELOG.md` に統合完了を記録
- `PIPELINE_UNIFICATION_PLAN.md` に完了マーク付与
- 最終コミット・PR 作成
**確認**: ドキュメント整合性 OK、PR レビュー準備完了

---

## 実装時の重要ルール（低性能LLM向け）

### 1. 1ステップ = 1ファイル / 1関数 / 1クラス の変更のみ
- 複数ファイル同時変更禁止
- 1ステップ完了ごとに動作確認コマンド実行

### 2. コピペ可能なコードスニペットを各ステップに記載済み
- 型ヒント完全装備（mypy で検証可能）
- 既存コードの命名規則・インデント厳守

### 3. 失敗したら前のステップに戻る、先に進まない
- テスト失敗 → マッピング/アダプタ修正 → 再テスト
- 例外発生 → try/except 追加 → 再テスト

### 4. フィーチャーフラグでロールバック可能に
- `USE_UNIFIED_PIPELINE=0` で旧実装に戻せる状態を Step 31 まで維持

### 5. 並行実行可能なステップ
| グループ | 並行可 |
|----------|--------|
| Phase A (1-5) | はい（独立） |
| Phase B (6-9) | はい（独立） |
| Phase C (10-16) | いいえ（順序依存） |
| Phase D (17-23) | いいえ（順序依存） |
| Phase E (24-30) | 部分可（API/CLI 独立） |
| Phase F (31-36) | いいえ（順序依存） |

---

## 完了判定基準

| 基準 | 目標 |
|------|------|
| テストカバレッジ | 統合パイプライン関連 80% 以上 |
| 回帰バグ | 0 件（既存全テストパス） |
| 実行時間 | 統合前 ±10% 以内 |
| コード行数 | 旧3ファイル合計(~1070行) → 新実装 < 800行 |
| 手動E2E | 全シナリオパス |

---

## 参照ファイル一覧（実装時によく読む）

| ファイル | 役割 |
|----------|------|
| `src/services/auto_workflow_pipeline.py` | ベースパイプライン（最重要） |
| `src/backend/workflows/full_auto_workflow.py` | 移植元：委譲先実装 |
| `src/backend/workflows/easy_mode_workflow.py` | 移植元：委譲先実装 |
| `src/easy_mode/pipeline.py` | 移植元：SpiceGuard・監査リライト・プリセット |
| `src/backend/workflows/_shared_ops.py` | 共通ユーティリティ（リトライ等） |
| `src/services/pipeline_steps.py` | 新Step実装群 |
| `src/services/audit_adapter.py` | 監査統一アダプタ |
| `src/services/spice_guard_adapter.py` | SpiceGuard統一アダプタ |
| `src/services/preset_loader.py` | プリセット統合ローダー |
| `src/services/progress_reporter.py` | 進捗アダプタ（Step 6-9で拡張） |
| `config/constants.py` | EP_CLIMAX, EP_FINAL 等 |
| `src/models/writing.py` | FullAutoWorkflowResult 定義 |

---

**以上。Step 1 から順に実装を進めてください。各 Step 完了時に「確認」コマンドを実行し、成功してから次へ進んでください。**