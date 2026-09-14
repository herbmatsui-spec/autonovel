# AutoNovel v4.5 集中実装計画書（全24ステップ）

低性能なLLMでも1ステップごとに確実な実装・検証（1ステップ＝1テスト緑）を行えるよう、コアアーキテクチャ・DAGスケジューラ・統一LLM・マルチメディア実DB結合・ブランチマージの主要未完パーツを全24ステップ（4パート構成）に分割した詳細設計。

## 📋 パート構成概要

| パート | ステップ | テーマ | 主な対象ファイル |
|---|---|---|---|
| Part 1 | Step 1〜6 | DAGスケジューラのタスクキャンセル・障害耐性堅牢化 | `src/backend/tasks/dag_scheduler.py`, `tests/unit/test_dag_scheduler.py` |
| Part 2 | Step 7〜12 | 統一LLMインターフェース規格 IUnifiedLLMClient の策定 | `src/core/llm/types.py`, `src/core/llm/unified_interface.py` |
| Part 3 | Step 13〜18 | SeriesDataLoader & 商用EPUB挿絵・口絵マニフェスト統合 | `src/backend/database/series_loader.py`, `src/services/exporters/epub_commercial_builder.py` |
| Part 4 | Step 19〜24 | IFルートマージ確定コミットAPI & フロントエンド競合解決プレビュー | `src/backend/services/branch_merge_service.py`, `frontend/src/components/branches/MergeConflictPreview.tsx` |

---

## ⚙️ Part 1: DAGスケジューラのタスクキャンセル・障害耐性堅牢化 (Step 1〜6)

### Step 1: DAGTaskState キャンセル状態の明確化
- **目的**: 実行中タスクが外部またはエラーで中断された際の `CANCELLED` 状態を正確に定義する。
- **対象ファイル**: `src/backend/tasks/dag_scheduler.py`
- **変更内容**:
  ```python
  from enum import Enum
  class DAGTaskState(str, Enum):
      PENDING = "pending"
      RUNNING = "running"
      COMPLETED = "completed"
      FAILED = "failed"
      CANCELLED = "cancelled"
  ```
- **確認コマンド**: `python -c "from src.backend.tasks.dag_scheduler import DAGTaskState; print(DAGTaskState.CANCELLED)"`
- **完了条件**: 状態列挙型に `CANCELLED` が追加されていること。

### Step 2: 実行中タスク追跡レジストリの追加
- **目的**: 現在非同期で走っている全タスクの `asyncio.Task` ハンドルを保持し、即時キャンセルを行えるようにする。
- **対象ファイル**: `src/backend/tasks/dag_scheduler.py`
- **変更内容**: `DAGScheduler` クラスに `self._running_tasks: dict[str, asyncio.Task] = {}` を追加。
- **確認コマンド**: `python -m py_compile src/backend/tasks/dag_scheduler.py`
- **完了条件**: タスク追跡辞書が初期化されること。

### Step 3: タスク障害発生時の依存先タスク一括キャンセル処理
- **目的**: あるタスクが失敗（`FAILED`）した際、それを上流に持つ未実行または実行中の下流タスクを安全に `CANCELLED` に遷移させる。
- **対象ファイル**: `src/backend/tasks/dag_scheduler.py`
- **変更内容**: `_cancel_downstream_tasks(self, failed_task_id: str)` メソッドを実装。
- **確認コマンド**: `python -m py_compile src/backend/tasks/dag_scheduler.py`
- **完了条件**: 下流キャンセルメソッドが実装されていること。

### Step 4: cancel_running_tasks メソッドの実装
- **目的**: 外部からのキャンセル要求を受け取り、`self._running_tasks` 内の全タスクに対して `.cancel()` を呼ぶ。
- **対象ファイル**: `src/backend/tasks/dag_scheduler.py`
- **変更内容**:
  ```python
  async def cancel_running_tasks(self):
      for task_id, t in list(self._running_tasks.items()):
          if not t.done():
              t.cancel()
  ```
- **確認コマンド**: `python -m py_compile src/backend/tasks/dag_scheduler.py`
- **完了条件**: キャンセルメソッドが完成すること。

### Step 5: test_scheduler_cancels_running_tasks_on_failure の修正・緑化
- **目的**: 既存の失敗テスト（`tests/unit/test_dag_scheduler.py`）を確実にパスさせる。
- **対象ファイル**: `tests/unit/test_dag_scheduler.py`
- **変更内容**: 意図した例外発生時に実行中タスクがキャンセル状態になることをアサート。
- **確認コマンド**: `pytest tests/unit/test_dag_scheduler.py -k test_scheduler_cancels_running_tasks_on_failure -v`
- **完了条件**: 該当テストが PASS すること。

### Step 6: Checkpoint 1 - DAGスケジューラテストの全緑化
- **目的**: DAGスケジューラの全単体テストを実行し、リグレッションがないことを確認。
- **確認コマンド**: `pytest tests/unit/test_dag_scheduler.py`
- **完了条件**: Checkpoint 1 が ALL GREEN であること。

---

## 🏛️ Part 2: 統一LLMインターフェース規格 IUnifiedLLMClient の策定 (Step 7〜12)

### Step 7: 共通LLMリクエスト・レスポンスモデルの定義
- **目的**: プロンプト、温度、トークン数、モデルを統一表現するデータ型を定義。
- **対象ファイル**: `src/core/llm/types.py` (新規作成)
- **変更内容**: `LLMRequest`, `LLMResponse`, `LLMUsage`, `StreamChunk` データクラスを実装。
- **確認コマンド**: `python -c "from src.core.llm.types import LLMRequest; print('OK')"`
- **完了条件**: 型定義が正しくインポートできること。

### Step 8: 抽象基底クラス IUnifiedLLMClient の定義
- **目的**: 同期／非同期、ストリーミング、構造化生成の抽象メソッドを規定。
- **対象ファイル**: `src/core/llm/unified_interface.py` (新規作成)
- **変更内容**: `generate`, `agenerate`, `stream`, `astream` を持つ抽象クラスを定義。
- **確認コマンド**: `python -c "from src.core.llm.unified_interface import IUnifiedLLMClient; print('OK')"`
- **完了条件**: 抽象クラスが定義されること。

### Step 9: モック統一クライアント UnifiedMockLLMClient の実装
- **目的**: テスト用の高速なモッククライアントを作成。
- **対象ファイル**: `src/core/llm/adapters/mock_unified_client.py` (新規作成)
- **変更内容**: `IUnifiedLLMClient` を継承し、固定テキストやJSONを返すモックを実装。
- **確認コマンド**: `python -m py_compile src/core/llm/adapters/mock_unified_client.py`
- **完了条件**: モックがコンパイルできること。

### Step 10: 旧 BaseLLMAdapter 向け後方互換ブリッジの実装
- **目的**: 既存の古いLLM呼び出しを新インターフェースへ安全に中継。
- **対象ファイル**: `src/services/llm/legacy_adapter_bridge.py` (新規作成)
- **変更内容**: `LegacyLLMBridge` クラスを定義。
- **確認コマンド**: `python -m py_compile src/services/llm/legacy_adapter_bridge.py`
- **完了条件**: 互換ブリッジが実装されていること。

### Step 11: 統一LLMインターフェース単体テストの作成
- **目的**: モッククライアントを用いて同期・非同期・ストリームの契約を検証。
- **対象ファイル**: `tests/unit/test_unified_llm_interface.py` (新規作成)
- **変更内容**: テストケースの記述。
- **確認コマンド**: `pytest tests/unit/test_unified_llm_interface.py -v`
- **完了条件**: 単体テストが成功すること。

### Step 12: Checkpoint 2 - 統一LLM基盤の検証
- **目的**: Part 2 の全テストを実行。
- **確認コマンド**: `pytest tests/unit/test_unified_llm_interface.py`
- **完了条件**: Checkpoint 2 が ALL GREEN であること。

---

## 📦 Part 3: SeriesDataLoader & 商用EPUB挿絵統合 (Step 13〜18)

### Step 13: SeriesDataLoaderConfig データクラスの定義
- **目的**: DBからシリーズデータを復元する際のオプションを定義。
- **対象ファイル**: `src/backend/database/series_loader.py` (新規作成)
- **変更内容**: `book_id`, `branch_id`, `include_unpublished` を保持するデータクラス実装。
- **確認コマンド**: `python -c "from src.backend.database.series_loader import SeriesDataLoaderConfig; print('OK')"`
- **完了条件**: クラスがインポートできること。

### Step 14: SeriesDataLoader.load_series の実装
- **目的**: DBの `books` および `chapters` テーブルからデータを取得し、`SeriesResult` を構築。
- **対象ファイル**: `src/backend/database/series_loader.py`
- **変更内容**: メタデータとチャプターリストの結合ロジックを実装。
- **確認コマンド**: `python -m py_compile src/backend/database/series_loader.py`
- **完了条件**: ローダーメソッドが実装されていること。

### Step 15: MultimediaService への SeriesDataLoader 統合
- **目的**: ダミーデータ生成（`make_minimal_series`）を廃止し、実DBローダーに完全に置き換え。
- **対象ファイル**: `src/backend/multimedia_service.py`
- **変更内容**: `_resolve_series` メソッドの追加とサービス内呼び出しの変更。
- **確認コマンド**: `python -m py_compile src/backend/multimedia_service.py`
- **完了条件**: 実DB参照に変更されること。

### Step 16: 商用EPUB挿絵アイテムモデル EpubIllustrationItem の定義
- **目的**: 口絵や章間挿絵のバイナリ、ファイル名、配置位置を管理する型定義。
- **対象ファイル**: `src/services/exporters/epub_manifest_builder.py`
- **変更内容**: `EpubIllustrationItem` データクラスの定義。
- **確認コマンド**: `python -c "from src.services.exporters.epub_manifest_builder import EpubIllustrationItem; print('OK')"`
- **完了条件**: クラスが定義されていること。

### Step 17: CommercialEpubBuilder への挿絵・口絵XHTML生成およびSpine配置
- **目的**: 挿絵画像をZIPに追加し、表紙直後の口絵や各章前の挿絵XHTMLを生成してSpineに挿入。
- **対象ファイル**: `src/services/exporters/epub_commercial_builder.py`
- **変更内容**: 挿絵ループとXHTML生成処理を追加。
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_commercial_builder.py`
- **完了条件**: 挿絵がEPUBに統合されること。

### Step 18: Checkpoint 3 - 実DBローダー & 挿絵EPUBの検証
- **目的**: Part 3 の関連テストを実行。
- **確認コマンド**: `pytest tests/unit/test_series_loader.py tests/unit/test_epub_illustrations.py`
- **完了条件**: Checkpoint 3 が ALL GREEN であること。

---

## 🌿 Part 4: ブランチマージ確定コミットAPI & フロントエンドプレビュー (Step 19〜24)

### Step 19: マージコミット用Pydanticスキーマの定義
- **目的**: 解決済みチャプター群とマージメッセージを受け取るリクエストモデルを定義。
- **対象ファイル**: `src/backend/schemas/branch.py`
- **変更内容**: `ResolvedChapterPayload`, `BranchMergeCommitRequest`, `BranchMergeCommitResponse` を定義。
- **確認コマンド**: `python -c "from src.backend.schemas.branch import BranchMergeCommitRequest; print('OK')"`
- **完了条件**: スキーマがインポートできること。

### Step 20: BranchMergeService の新規作成とアトミック更新
- **目的**: 競合解決されたテキストをターゲットブランチの章に安全に永続化するサービスクラスを作成。
- **対象ファイル**: `src/backend/services/branch_merge_service.py` (新規作成)
- **変更内容**: `commit_merge()` メソッドの実装。
- **確認コマンド**: `python -m py_compile src/backend/services/branch_merge_service.py`
- **完了条件**: サービスクラスがコンパイルできること。

### Step 21: FastAPI マージコミットエンドポイントの追加
- **目的**: `/api/branches/merge/commit` エンドポイントを実装し、サービス層へ委譲。
- **対象ファイル**: `src/backend/routers/branches.py`
- **変更内容**: ルータ関数の追加とエラーハンドリング。
- **確認コマンド**: `python -m py_compile src/backend/routers/branches.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 22: フロントエンド MergeConflictPreview.tsx の競合テキスト編集UI拡充
- **目的**: ユーザーが Base / Source / Target の差異を視認し、手動編集して確定できるReactコンポーネントの完成。
- **対象ファイル**: `frontend/src/components/branches/MergeConflictPreview.tsx`
- **変更内容**: 比較ビューアーとマージ実行ボタンのアクション結び付け。
- **確認コマンド**: `npx tsc --noEmit`
- **完了条件**: TypeScriptコンパイルエラーが0件であること。

### Step 23: ブランチマージ確定の統合テスト作成
- **目的**: API経由でマージコミットを実行し、DB上のチャプター内容が正しく更新されるかをテスト。
- **対象ファイル**: `tests/unit/test_branch_merge_commit.py` (新規作成)
- **変更内容**: マージ確定テストケースの実装。
- **確認コマンド**: `pytest tests/unit/test_branch_merge_commit.py -v`
- **完了条件**: 統合テストが合格すること。

### Step 24: Checkpoint 4 - 全体ビルド & 総合テスト検証
- **目的**: 全バックエンドテストとフロントエンド型チェックを一括実行。
- **確認コマンド**: `pytest && npx tsc --noEmit`
- **完了条件**: 全テストが ALL GREEN かつ TypeScriptビルドが成功すること。
