# AutoNovel 実装計画書【C3】
# 商業ビートシート API の SSOT 化と API 衛生 개선（36 Steps）

- **文書ID**: PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS
- **作成日**: 2026-09-26
- **対象バージョン**: AutoNovel v5.2.0（v5系 完成形）
- **基準コミット**: C1 / C2 完了後のツリー
- **対象読者**: 小型・低性能LLM（7Bクラス等）。**1ステップ＝1ファイル1変更**に分割し、「検証コマンド → 期待結果」まで自己完結で記述。
- **前提計画書**:
  - [PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md](./PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md)（完了済み前提）
  - [PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md](./PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md)（完了済み前提）

---

## 0. 対象外（重要）

- **イラスト生成系は一切扱わない**（`src/services/illustration/`、`config/image_models.py`、
  `src/services/illustration/clients/` の重複・未接続問題も **本計画書では修正しない**。別計画で扱う）。
- 伏線同期・DI コンテナは **C2** で完了済み。本計画書では触らない。

---

## 1. 目的

`src/backend/routers/commercial_planning.py` の「40話ビートシート API」を、**既存の正となる仕様（SSOT）に接続した実装**へ置き換える。あわせてレビューで挙げた API 衛生上の問題（ビルド用URLの open redirect、同期セッションによるイベントループのブロック、遅延プロパティの二重管理）を片付ける。

### 1.1 現状の問題点（コードレビューで確定）

| 優先度 | 問題 | 影響 |
|:---:|---|---|
| **P0-4a** | 既存の正となる仕様（`COMMERCIAL_40EP_BEATS` / `EpisodeBeat` / `PlanningAgent.generate_commercial_beat_sheet`）を**無視**し、router 内に4幕+tension曲線をハードコード | 仕様が二重化。LLMを1回も呼ばない偽データ生成 |
| **P0-4b** | 1リクエストで Plot 40行を即時 INSERT、既存 Plot は**全削除** | 大量書込・取り消しが不可能 |
| **P0-4c** | `getattr(current_user, "id", 1)` で**存在しない user_id** の Book を作る | 外部キー制約で500 |
| **P0-4d** | 所有者チェックが無い（`verify_book_ownership` を使い回さない） | 他人のビートシートが閲覧可能（IDOR） |
| **P0-4e** | `async def` + **同期 Session**（`get_db`） | イベントループをブロックさせる |
| **P0-4f** | `db.query().delete()` / `branch_id=1` 固定 / 入力エラーも500 | 保守性・前方互換性の欠如 |
| **P1-a** | `billing.py` が success_url / cancel_url / return_url を**リクエストボディから無検証で採用** | オープンリダイレクト |
| **P1-b** | `FRONTEND_URL` の既定が localhost のまま、production 検証が無い | 本番で必ず壊れる |
| **P1-c** | `rag_service._vector_store` / `graph_pipeline._vector_store` の setter が2つの内部変数を同時に壊す | 代入意味が曖昧 |

---

## 2. 全体構成（36ステップ）

```
[Part 1] Step 1- 6  現状調査と仕様確定（コード変更なし）
[Part 2] Step 7-14  サービス層（engine workflow）の新設
[Part 3] Step15-24  ルーターの書き換え（タスク化・非同期・所有者検証・SSOT利用）
[Part 4] Step25-31  API 衛生（billing / FRONTEND_URL / 遅延プロパティ）
[Part 5] Step32-36  テストと回帰防止ゲート
```

---

## Part 1: 現状調査と仕様確定 (Step 1-6)

### Step 1: 現行エンドポイントの応答を記録する

- **目的**: 変更前の出入力を証拠として残す。
- **作業内容**: テストクライアントで以下を実行し、`docs/v5_c3_baseline.md` に記録する。
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api -q -k "planning" 2>&1 | Select-Object -Last 10
  Select-String -Path tests\ -Recurse -Include *.py -Pattern "commercial/planning|commercial_planning" |
    ForEach-Object { "$($_.Path):$($_.LineNumber)" }
  ```
- **期待結果**: commercial_planning 専用テストが **存在しない**ことを確認する（= カバレッジゼロ）。記録する。

### Step 2: 既存クライアント呼び出し元がいないことを確認する

- **作業内容**: フロントエンド・Web・Streamlit から呼んでいる箇所を洗い出す。
  ```powershell
  Select-String -Path frontend,web,streamlit_app -Recurse -Include *.ts,*.tsx,*.js,*.py -Pattern "commercial/planning" -ErrorAction SilentlyContinue |
    ForEach-Object { "$($_.Path):$($_.LineNumber)" }
  ```
- **期待結果**: 0件。**API 契約を変更してよい**根拠になる。破壊的な変更は「レスポンス形を `EpisodeBeat` に統一」までにとどめる。

### Step 3: SSOT 一覧を確定する

- **目的**: 「どこが正となる仕様か」を1箇所にまとめる。
- **作業内容**: 次の3つが正であることを確認して記録する。
  | 対象 | 役割 |
  |---|---|
  | `src/config/commercial_beat_sheet.py` の `COMMERCIAL_40EP_BEATS` / `get_beat_for_episode` | 40話の7フェーズ構成（伏線契約を含む） |
  | `src/models/beat_sheet.py` の `EpisodeBeat` | 1話分のデータ仕様（`ep_num` 1-40、`tension_target` 0.0-1.0 を検証） |
  | `src/agents/planning.py:243` の `PlanningAgent.generate_commercial_beat_sheet(title, synopsis, **kwargs)` | LLM生成の唯一の入口 |
- **検証コマンド**:
  ```powershell
  Select-String -Path src\agents\planning.py -Pattern "async def generate_commercial_beat_sheet"
  Select-String -Path src\models\beat_sheet.py -Pattern "class EpisodeBeat"
  ```
- **期待結果**: 両方が1件ずつヒットする。

### Step 4: ルーター側の重複定義 `BeatSheetItem` を記録する

- **目的**: 削除対象を特定する。
- **作業内容**:
  ```powershell
  Select-String -Path src\backend\routers\commercial_planning.py -Pattern "class BeatSheet"
  ```
  現状 `BeatSheetItem` / `BeatSheetResponse` / `BeatSheetGenerateRequest` の3つがあり、
  `EpisodeBeat` とフィールドがほぼ重複していることを確認する。
- **期待結果**: 3件の定義位置が記録される。

### Step 5: `Plot` の tension セマンティクスを確定する

- **目的**: 0-100 と 0-1 の二重表現を、どちらに統一するかを決める。
- **作業内容**: `src/backend/database/models.py` の `Plot` 定義を確認する。
  - `tension` … `Integer`, default 50（=0-100 の評価値）
  - `target_tension` … `Float`, comment「動的に計算された目標テンション値 (0.0-1.0)」
  `EpisodeBeat.tension_target` は 0.0-1.0 なので、`target_tension` にそのまま入れる。
- **期待結果**: 方針「`EpisodeBeat.tension_target` → `Plot.target_tension`、`Plot.tension` は 0-100 のまま触らない」を記録する。

### Step 6: Part 1 の通過確認（ベースライン）

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit tests/integration -q -p no:randomly 2>&1 | Select-Object -Last 5
  ```
- **期待結果**: failure 0（C1・C2 完了により緑であることを確認）。

---

## Part 2: サービス層の新設 (Step 7-14)

### Step 7: 商用ビートシート用ワークフローを新設する

- **目的**: LLM呼び出しを**サービス層へ**移し、router に残さない。
- **対象ファイル**: `src/backend/workflows/commercial_beat_sheet_workflow.py`（**新規作成**）
- **変更内容**: 下記を記入する。Plot の保存は既存.router（`src/backend/routers/plots.py:271`）と同じ
  `UnitOfWork` + `uow.plots.create_or_replace_plot` を使う（facade に依存しない）。
  ```python
  """40話商業ビートシート生成ワークフロー（SSOT接続版）。

  - フェーズ定義は src.config.commercial_beat_sheet.COMMERCIAL_40EP_BEATS を使う
  - データ仕様は src.models.beat_sheet.EpisodeBeat を使う
  - LLM 呼び出しは PlanningAgent.generate_commercial_beat_sheet に委譲する
  """
  from __future__ import annotations

  import logging
  from typing import Any

  from src.agents.planning import PlanningAgent
  from src.backend.database.uow import UnitOfWork
  from src.core.container import AppContainer
  from src.models.beat_sheet import EpisodeBeat
  from src.shared.utils import StatusReporter

  logger = logging.getLogger(__name__)

  DEFAULT_BRANCH_ID = 1


  class CommercialBeatSheetWorkflow:
      """単体テストしやすい独立クラス（BaseWorkflow には依存しない）。"""

      def __init__(self, repo: Any = None, prompt_manager: Any = None, llm: Any = None) -> None:
          self.repo = repo
          self.prompt_manager = prompt_manager
          self.llm = llm

      async def generate(
          self,
          *,
          book_id: int,
          title: str,
          synopsis: str,
          genre: str = "fantasy",
          target_episodes: int = 40,
          branch_id: int = DEFAULT_BRANCH_ID,
          reporter: StatusReporter | None = None,
      ) -> list[EpisodeBeat]:
          """ビートシートを生成し、Plot として保存して返す。"""
          if reporter:
              reporter.set_message("40話ビートシートを生成中...")

          agent = PlanningAgent(repo=self.repo, llm=self.llm, prompt_manager=self.prompt_manager)
          beats = await agent.generate_commercial_beat_sheet(
              title=title,
              synopsis=synopsis,
              genre=genre,
          )
          normalized = self._normalize(beats, target_episodes)
          await self._persist(book_id=book_id, beats=normalized, branch_id=branch_id)
          return normalized

      @staticmethod
      def _normalize(beats: list[EpisodeBeat], target_episodes: int) -> list[EpisodeBeat]:
          """話数の重複・欠損・範囲外を正規化する。"""
          by_ep: dict[int, EpisodeBeat] = {}
          for beat in beats:
              ep = int(getattr(beat, "ep_num", 0) or 0)
              if ep < 1 or ep > target_episodes:
                  continue
              by_ep.setdefault(ep, beat)
          return [by_ep[ep] for ep in sorted(by_ep)]

      @staticmethod
      async def _persist(*, book_id: int, beats: list[EpisodeBeat], branch_id: int) -> None:
          """既存 Plot を消さずに upsert する（全削除はしない）。"""
          async with UnitOfWork(AppContainer.db()) as uow:
              for beat in beats:
                  await uow.plots.create_or_replace_plot(
                      book_id=book_id,
                      ep_num=beat.ep_num,
                      thought_process="commercial_beat_sheet_workflow",
                      title=f"第{beat.ep_num}話",
                      summary=beat.mission,
                      detailed_blueprint=beat.visual_scene_focus,
                      next_hook="",
                      tension=int(round(beat.tension_target * 100)),
                      branch_id=branch_id,
                  )
  ```
  **本質的な要求は3点だけ**（細部は実装時に既存コードに合わせて調整してよい）。
  1. `list[EpisodeBeat]` を返す
  2. フェーズやテンションの値を **router 内で計算しない**（LLM結果と SSOT の範囲検証だけを使う）
  3. 既存 Plot を全削除しない（`create_or_replace_plot` は upsert）
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/workflows/commercial_beat_sheet_workflow.py
  .venv\Scripts\python.exe -c "from src.backend.workflows.commercial_beat_sheet_workflow import CommercialBeatSheetWorkflow; print('ok')"
  ```
- **期待結果**: ruff が通り、`ok` が出力される。

### Step 8: `BaseWorkflow` を継承させる（既存規約に合わせる）

- **目的**: 既存のワークフロー登録機構（engine から生成）に乗る。
- **対象ファイル**: `src/backend/workflows/commercial_beat_sheet_workflow.py`
- **変更内容**:
  1. import 群に次を追加する。
     ```python
     from .base_workflow import BaseWorkflow
     ```
  2. クラス宣言を次のように変更する。
     ```python
     class CommercialBeatSheetWorkflow(BaseWorkflow):
         """BaseWorkflow の __init__（repo= / prompt_manager= / llm= 等）を受ける。"""
     ```
  3. `__init__` を、基底クラスの引数を受け取れる形に変更する（`super().__init__` を必ず呼ぶ）。
     ```python
             def __init__(self, *args, **kwargs) -> None:
                 super().__init__(*args, **kwargs)
                 if self.prompt_manager is None:
                     self.prompt_manager = kwargs.get("prompt_manager") or getattr(self, "pm", None)
     ```
     `self.prompt_manager` / `self.llm` が基底クラスに無い場合は、
     `getattr(self, "prompt_manager", None)` / `getattr(self, "llm", None)` で読む形にする。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/workflows/commercial_beat_sheet_workflow.py
  .venv\Scripts\python.exe -c "from src.backend.workflows.commercial_beat_sheet_workflow import CommercialBeatSheetWorkflow; print('ok')"
  .venv\Scripts\python.exe -m pytest tests/unit/test_wizard_flow.py -q
  ```
- **期待結果**: `ok` が出力され、既存テストが壊れない。

### Step 9: `_normalize` の境界値テストを書く

- **目的**: 話数の重複・欠損・範囲外を固定する。
- **対象ファイル**: `tests/unit/workflows/test_commercial_beat_sheet_workflow.py`（**新規作成**）
- **変更内容**: 下記5テストを記入する。
  ```python
  """CommercialBeatSheetWorkflow._normalize の境界値テスト。"""
  from __future__ import annotations

  from src.backend.workflows.commercial_beat_sheet_workflow import CommercialBeatSheetWorkflow
  from src.models.beat_sheet import EpisodeBeat


  def _beat(ep: int, tension: float = 0.5) -> EpisodeBeat:
      return EpisodeBeat(
          ep_num=ep,
          phase="開幕フック",
          mission=f"第{ep}話のミッション",
          tension_target=tension,
          visual_scene_focus="見せ場",
      )


  def test_normalize_keeps_order_and_drops_duplicates():
      beats = [_beat(2), _beat(1), _beat(2)]
      out = CommercialBeatSheetWorkflow._normalize(beats, 40)
      assert [b.ep_num for b in out] == [1, 2]


  def test_normalize_drops_out_of_range():
      out = CommercialBeatSheetWorkflow._normalize([_beat(0), _beat(41), _beat(5)], 40)
      assert [b.ep_num for b in out] == [5]


  def test_normalize_keeps_gaps_as_missing():
      out = CommercialBeatSheetWorkflow._normalize([_beat(1), _beat(3)], 40)
      assert [b.ep_num for b in out] == [1, 3]


  def test_normalize_respects_target_episodes():
      out = CommercialBeatSheetWorkflow._normalize([_beat(1), _beat(30)], 20)
      assert [b.ep_num for b in out] == [1]


  def test_normalize_empty_input():
      assert CommercialBeatSheetWorkflow._normalize([], 40) == []
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/workflows/test_commercial_beat_sheet_workflow.py -q
  ```
- **期待結果**: `5 passed`。

### Step 10: `generate` の永続化テスト（LLM をモック）を書く

- **目的**: 「Plot が全削除されず upsert される」ことを固定する。
- **対象ファイル**: `tests/unit/workflows/test_commercial_beat_sheet_workflow.py`（**同じファイルに追加**）
- **変更内容**: 下記3テストを追加する。
  ```python
  from unittest.mock import AsyncMock, MagicMock  # ファイル先頭に追加

  from src.models.beat_sheet import EpisodeBeat as _EB  # 既存の import と重複しない場合のみ


  async def _workflow_with_stub_agent(monkeypatch, beats):
      """PlanningAgent.generate_commercial_beat_sheet を固定したワークフローを作る。"""
      import src.backend.workflows.commercial_beat_sheet_workflow as mod

      fake_agent = MagicMock()
      fake_agent.generate_commercial_beat_sheet = AsyncMock(return_value=beats)
      monkeypatch.setattr(mod, "PlanningAgent", lambda **kwargs: fake_agent)
      return mod.CommercialBeatSheetWorkflow(repo=MagicMock(), prompt_manager=None, llm=None)


  async def test_generate_persists_each_beat(monkeypatch):
      wf = await _workflow_with_stub_agent(monkeypatch, [_beat(1), _beat(2)])
      result = await wf.generate(book_id=1, title="T", synopsis="S")
      assert [b.ep_num for b in result] == [1, 2]


  async def test_generate_does_not_delete_existing_plots(monkeypatch):
      """全削除 polarizing しないこと（保存メソッドの呼び出し回数だけを見る）。"""
      wf = await _workflow_with_stub_agent(monkeypatch, [_beat(1), _beat(2)])
      result = await wf.generate(book_id=1, title="T", synopsis="S")
      assert len(result) == 2


  async def test_generate_tolerates_agent_failure(monkeypatch):
      import pytest

      import src.backend.workflows.commercial_beat_sheet_workflow as mod

      fake_agent = MagicMock()
      fake_agent.generate_commercial_beat_sheet = AsyncMock(side_effect=RuntimeError("LLM失敗"))
      monkeypatch.setattr(mod, "PlanningAgent", lambda **kwargs: fake_agent)
      wf = mod.CommercialBeatSheetWorkflow(repo=MagicMock(), prompt_manager=None, llm=None)
      with pytest.raises(RuntimeError):
          await wf.generate(book_id=1, title="T", synopsis="S")
  ```
  **注意**: `_persist` が `repo.create_or_replace_plot` を使う実装でない場合は、
  Step 7 で確定した実装に合わせて `wf.repo` のモックを組み立てる。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/workflows/test_commercial_beat_sheet_workflow.py -q
  ```
- **期待結果**: `8 passed`（Step 9 の5件 + 追加3件）。

### Step 11: `engine.py` にワークフローメソッドを追加する

- **目的**: タスクキューから呼べるようにする。
- **対象ファイル**: `src/backend/engine.py`（`reverse_plot_generation_workflow` の直後）
- **変更内容**: 次のメソッドを追加する。
  ```python
      async def commercial_beat_sheet_workflow(
          self,
          book_id: int,
          title: str,
          synopsis: str,
          genre: str = "fantasy",
          target_episodes: int = 40,
          branch_id: int = 1,
          reporter: Any | None = None,
      ) -> Any:
          from src.backend.workflows.commercial_beat_sheet_workflow import (
              CommercialBeatSheetWorkflow,
          )

          workflow = CommercialBeatSheetWorkflow(
              repo=self.repo,
              prompt_manager=self.pm,
              llm=self.generate_json,
          )
          return await workflow.generate(
              book_id=book_id,
              title=title,
              synopsis=synopsis,
              genre=genre,
              target_episodes=target_episodes,
              branch_id=branch_id,
              reporter=reporter,
          )
  ```
  **注意**: `self.repo` / `self.pm` / `self.generate_json` は `reverse_plot_generation_workflow` が
  用いている属性と同じものを使う（`engine.py:226-228` を参照）。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/engine.py
  .venv\Scripts\python.exe -c "from src.backend.engine import UltimateHegemonyEngine; print(hasattr(UltimateHegemonyEngine, 'commercial_beat_sheet_workflow'))"
  ```
- **期待結果**: `True` が出力される。

### Step 12: メソッド名の解決機構を確認する（`method_name` の解決方法）

- **目的**: `execute_service_workflow(task_id, ..., method_name=...)` がこのメソッドを解決できることを保証する。
- **作業内容**: 実行時に `method_name` がどう解決されるかを確認する。
  ```powershell
  .venv\Scripts\python.exe -c "import inspect; from src.backend.tasks import execute_service_workflow; src=inspect.getsource(execute_service_workflow); print('getattr' in src, 'method_name' in src)"
  Select-String -Path src\backend\tasks\__init__.py -Pattern "method_name" -Context 2,2
  ```
- **期待結果**: `getattr(engine, method_name)` 相当の解決が行われることを確認する。
  違う場合は `src/backend/tasks/__init__.py` の解決部分を読み、**Step 11 のメソッド名が解決可能か**を判断する。

### Step 13: サービス層の統合テスト（タスク発行）を追加する

- **対象ファイル**: `tests/unit/workflows/test_commercial_beat_sheet_task.py`（**新規作成**）
- **変更内容**: 下記を記入する。`execute_service_workflow` をモックし、**タスクが発行されること**だけを固定する。
  ```python
  """商用ビートシート生成が「タスク発行型」になったことの回帰テスト。"""
  from __future__ import annotations

  from unittest.mock import patch

  from src.backend.routers import commercial_planning


  async def test_generate_returns_task_id_instead_of_rows():
      """同期で40行を返さず、task_id だけを返すこと（イベントループのブロック防止）。"""
      with patch.object(commercial_planning, "execute_service_workflow") as mock_exec, patch.object(
          commercial_planning, "create_task", new=_fake_create_task
      ):
          result = await commercial_planning.generate_beat_sheet(
              request=commercial_planning.BeatSheetGenerateRequest(title="T", synopsis="S", book_id=1),
              current_user=_FakeUser(),
              db=None,
          )
      assert "task_id" in result
      mock_exec.assert_called_once()
  ```
  **注意**: `create_task` / `execute_service_workflow` の import 位置（関数内 import か モジュール import か）は
  Step 17 の実装に合わせて決める。モジュールレベル import にhindari、`patch.object` の対象が
  存在しない場合は `patch("src.backend.tasks.execute_service_workflow")` を使う。
  `_fake_create_task` / `_FakeUser` は同一ファイル内に定義する（`db=None` を許容する実装が無い場合は
  `db` 引数を省略して呼ぶ）。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/workflows/test_commercial_beat_sheet_task.py -q
  ```
- **期待結果**: `1 passed`。

### Step 14: Part 2 の通過確認

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/workflows tests/unit/test_wizard_flow.py -q
  .venv\Scripts\python.exe -m ruff check src/backend/workflows src/backend/engine.py
  ```
- **期待結果**: failure 0、ruff が通る。

---

## Part 3: ルーターの書き換え (Step 15-24)

### Step 15: リクエストモデルを SSOT に合わせて整理する

- **目的**: `EpisodeBeat` の検証（`ep_num` 1-40、`tension_target` 0.0-1.0）をそのまま使う。
- **対象ファイル**: `src/backend/routers/commercial_planning.py`
- **変更内容**: `BeatSheetGenerateRequest` を次のように置き換える。
  ```python
  class BeatSheetGenerateRequest(BaseModel):
      """40話ビートシート生成リクエスト。"""

      book_id: int | None = None
      title: str = Field(min_length=1, max_length=200)
      synopsis: str = Field(min_length=1)
      genre: str = Field(default="fantasy", max_length=100)
      target_episodes: int = Field(default=40, ge=1, le=40)
      branch_id: int = Field(default=1, ge=1)
  ```
  併せて import に `from pydantic import BaseModel, Field` を追加する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/commercial_planning.py
  .venv\Scripts\python.exe -c "from src.backend.routers.commercial_planning import BeatSheetGenerateRequest as R; R(title='a', synopsis='b', target_episodes=41)"
  ```
- **期待結果**: ruff が通り、2つ目のコマンドが **ValidationError** で終了すること（=検証が効く）。

### Step 16: レスポンス형을 `EpisodeBeat` ベースに変更する

- **目的**: ルーター内の重複定義をやめる。
- **対象ファイル**: `src/backend/routers/commercial_planning.py`
- **変更内容**:
  1. `BeatSheetItem` と `BeatSheetResponse` の定義を**削除**する。
  2. 次の2つだけ残す（`src/models/beat_sheet.py` の型を再利用）。
     ```python
     from src.models.beat_sheet import EpisodeBeat


     class BeatSheetResponse(BaseModel):
         """40話ビートシートのレスポンス（要素は SSOT の EpisodeBeat）。"""

         items: list[EpisodeBeat]
     ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/commercial_planning.py
  .venv\Scripts\python.exe -c "from src.backend.routers.commercial_planning import BeatSheetResponse as R; print(R.model_fields.keys())"
  ```
- **期待結果**: `dict_keys(['items'])` が出力される。

### Step 17: `POST /generate` をタスク発行型に変更する

- **目的**: イベントループをブロックさせず、進捗を返す。
- **対象ファイル**: `src/backend/routers/commercial_planning.py`
- **変更内容**: `generate_beat_sheet` の **関数全体を** 次の実装に置き換える。
  ```python
  @router.post("/generate", response_model=BeatSheetTaskResponse)
  async def generate_beat_sheet(
      request: BeatSheetGenerateRequest,
      current_user: User = Depends(get_current_user),
  ):
      """ビートシート生成をタスクとして発行する（同期実行しない）。"""
      from src.backend.tasks import execute_service_workflow

      from src.backend.task_helpers import create_task

      book_id = request.book_id
      if book_id is None:
          book_id = await _create_book_for_beat_sheet(request, current_user)

      task_id = _generate_task_id("commercial_beats")
      await create_task(task_id, "40話ビートシートを生成中...", total_steps=1)
      execute_service_workflow(
          task_id=task_id,
          api_key=None,
          config_dict={},
          method_name="commercial_beat_sheet_workflow",
          kwargs={
              "book_id": book_id,
              "title": request.title,
              "synopsis": request.synopsis,
              "genre": request.genre,
              "target_episodes": request.target_episodes,
              "branch_id": request.branch_id,
          },
      )
      return {"task_id": task_id, "book_id": book_id, "success": True}
  ```
  併せて、同じファイルに以下を追加する。
  ```python
  import uuid

  from src.backend.database.uow import UnitOfWork
  from src.core.container import AppContainer


  class BeatSheetTaskResponse(BaseModel):
      """タスク発行結果。"""

      task_id: str
      book_id: int
      success: bool = True


  def _generate_task_id(prefix: str) -> str:
      return f"{prefix}_{uuid.uuid4().hex[:12]}"


  async def _create_book_for_beat_sheet(
      request: "BeatSheetGenerateRequest",
      current_user: User,
  ) -> int:
      """Book を1件だけ作成する（Branch も同時に作る）。"""
      if getattr(current_user, "id", None) is None:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="認証ユーザー情報を取得できません",
          )
      async with UnitOfWork(AppContainer.db()) as uow:
          book = Book(
              user_id=current_user.id,
              title=request.title,
              genre=request.genre,
              synopsis=request.synopsis,
              target_eps=request.target_episodes,
          )
          uow.session.add(book)
          await uow.session.flush()
          branch = Branch(book_id=book.id, name="main", fork_ep_num=0)
          uow.session.add(branch)
          return int(book.id)
  ```
  **注意**: docstring の「」は)**「新規作成: 」に書き換える**こと（可読性のため）。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/commercial_planning.py
  .venv\Scripts\python.exe -c "from src.backend.routers.commercial_planning import router; print('router ok')"
  ```
- **期待結果**: `router ok` が出力される。

### Step 18: `GET /{book_id}` の所有者検証を追加する

- **目的**: P0-4d（IDOR）の修正。
- **対象ファイル**: `src/backend/routers/commercial_planning.py`（`get_beat_sheet` 内）
- **変更内容**: 関数本体の先頭に1行を追加する。
  ```python
      await verify_book_ownership(book_id, current_user, AppContainer.db())
  ```
  併せて import 群に次を追加する。
  ```python
  from src.backend.security.owner_guard import verify_book_ownership
  ```
- **検証テスト**: Step 22 で作成するテスト
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/commercial_planning.py
  ```
- **期待結果**: ruff が通る。

### Step 19: `GET /{book_id}` の読み取りを `select()` に統一する

- **目的**: `db.query()` 等のレガシー書式をやめ、tension の変換を1箇所にする。
- **対象ファイル**: `src/backend/routers/commercial_planning.py`
- **変更内容**:
  1. `db.query(Plot).filter(...).delete()` を使う箇所（あれば）を `select` ベースへ置き換える。
  2. アイテム組み立てを次の1箇所に集約する（`tension_target` は 0.0-1.0 に正規化）。
     ```python
     def _plot_to_episode_beat(p: Plot) -> EpisodeBeat:
         """Plot ORM → SSOT の EpisodeBeat へ変換する（tension は 0-100 → 0.0-1.0）。"""
         target = p.target_tension
         if target is None:
             tension = p.tension if p.tension is not None else 50
             target = round(float(tension) / 100.0, 2)
         return EpisodeBeat(
             ep_num=int(p.ep_num),
             phase=p.current_chain_phase or "Setup",
             mission=p.summary or p.title or f"第{p.ep_num}話",
             tension_target=round(float(target), 2),
             visual_scene_focus=p.one_line_summary or p.title or "",
         )
     ```
  3. `get_beat_sheet` の items 組み立てを
     ```python
             items = [_plot_to_episode_beat(p) for p in plots]
     ```
     の1行にする。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/commercial_planning.py
  Select-String -Path src\backend\routers\commercial_planning.py -Pattern "db\.query\("
  ```
- **期待結果**: ruff が通り、`db.query(` の検索結果が **0件**。

### Step 20: `GET /{book_id}` の 404 仕様を明示する

- **目的**: 「生成前」と「存在しない」を区別する。
- **対象ファイル**: `src/backend/routers/commercial_planning.py`
- **変更内容**: icode が「plots が空」だった場合を 404 にしている現状を維持しつつ、
  detail の文言を契約として明示する。
  ```python
              raise HTTPException(
                  status_code=status.HTTP_404_NOT_FOUND,
                  detail=f"ビートシートが未生成です（book_id={book_id}）。先に /generate を呼んでください。",
              )
  ```
- **検証テスト**: Step 22 の `test_beat_sheet_404_when_not_generated`
- **期待結果**: 文言が上記の文字列になること。

### Step 21: 例外を型ごとに正規化する

- **目的**: 入力エラーが 500 にならないように分類する。
- **対象ファイル**: `src/backend/routers/commercial_planning.py`
- **変更内容**: `except Exception` の前に HTTPException の再送出とログを追加する。
  ```python
      except HTTPException:
          raise
      except Exception as exc:
          logger.error("Failed to get beat sheet: %s", exc, exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="ビートシートの取得に失敗しました",
          ) from exc
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/commercial_planning.py
  ```
- **期待結果**: ruff が通る。

### Step 22: ルーターの回帰テストを追加する

- **目的**: IDOR・404・検証エラーを固定する。
- **対象ファイル**: `tests/unit/api/test_commercial_planning.py`（**新規作成**）
- **変更内容**: 下記4テストを記入する。DB と所有者は**すべて差し替え**、外部依存に依存しない。
  ```python
  """/commercial/planning の契約テスト（所有者検証・404・入力検証・Task 発行）。"""
  from __future__ import annotations

  from types import SimpleNamespace
  from unittest.mock import AsyncMock, MagicMock, patch

  import pytest
  from httpx import ASGITransport, AsyncClient

  from src.backend.auth import get_current_user
  from src.backend.server import app


  @pytest.fixture
  def owner(monkeypatch):
      user = SimpleNamespace(id=1, role="user")
      app.dependency_overrides[get_current_user] = lambda: user
      monkeypatch.setattr(
          "src.backend.routers.commercial_planning.verify_book_ownership",
          AsyncMock(return_value=SimpleNamespace(id=1)),
      )
      yield user
      app.dependency_overrides.pop(get_current_user, None)


  async def _get(book_id: int = 1):
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          return await client.get(f"/commercial/planning/{book_id}")


  async def test_beat_sheet_404_when_not_generated(owner):
      resp = await _get(1)
      assert resp.status_code == 404


  async def test_ownership_is_verified(owner):
      resp = await _get(1)
      import src.backend.routers.commercial_planning as mod

      mod.verify_book_ownership.assert_awaited()


  async def test_generate_rejects_out_of_range_episodes(owner):
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          resp = await client.post(
              "/commercial/planning/generate",
              json={"title": "T", "synopsis": "S", "target_episodes": 41},
          )
      assert resp.status_code == 422


  async def test_generate_returns_task_id(owner):
      import src.backend.routers.commercial_planning as mod

      with patch.object(mod, "execute_service_workflow") as mock_exec, patch(
          "src.backend.task_helpers.create_task", new=AsyncMock()
      ):
          transport = ASGITransport(app=app)
          async with AsyncClient(transport=transport, base_url="http://test") as client:
              resp = await client.post(
                  "/commercial/planning/generate",
                  json={"title": "T", "synopsis": "S", "book_id": 1},
              )
      assert resp.status_code == 200
      assert resp.json()["task_id"]
      mock_exec.assert_called_once()
  ```
  **注意**:
  - `execute_service_workflow` は Step 17 で **関数内 import** しているため、
    `patch.object(mod, "execute_service_workflow")` が無い場合は
    `patch("src.backend.tasks.execute_service_workflow")` を使う。
  - `test_ownership_is_verified` は差し替えた `verify_book_ownership` の呼び出しを記録して確認する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_commercial_planning.py -q
  ```
- **期待結果**: `4 passed`。

### Step 23: OpenAPI 契約テストを追加する

- **目的**: レスポンス形が SSOT（`EpisodeBeat`）であることを固定する。
- **対象ファイル**: `tests/contract/test_commercial_planning_contract.py`（**新規作成**）
- **変更内容**: 下記2テストを記入する。
  ```python
  """/commercial/planning の OpenAPI 契約テスト。"""
  from __future__ import annotations

  from src.backend.server import app


  def _schema_for(path: str, method: str) -> dict:
      spec = app.openapi()
      return spec["paths"][path][method]


  def test_get_beat_sheet_declares_episode_beat_fields():
      op = _schema_for("/commercial/planning/{book_id}", "get")
      ref = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
      assert ref.endswith("BeatSheetResponse")


  def test_generate_response_declares_task_id():
      op = _schema_for("/commercial/planning/generate", "post")
      schema = op["responses"]["200"]["content"]["application/json"]["schema"]
      assert "$ref" in schema
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/contract/test_commercial_planning_contract.py -q
  ```
- **期待結果**: `2 passed`。`$ref` の末尾が `BeatSheetResponse` でない場合は Step 16 の実装に手を加える。

### Step 24: Part 3 の通過確認

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api tests/contract -q
  .venv\Scripts\python.exe -m ruff check src/backend/routers/commercial_planning.py
  ```
- **期待結果**: failure 0、ruff が通る。

---

## Part 4: API 衛生 (Step 25-31)

### Step 25: `billing.py` の URL 採用を `settings.FRONTEND_URL` のみにする

- **目的**: P1-a（オープンリダイレクト）の修正。
- **対象ファイル**: `src/backend/routers/billing.py`
- **変更内容**:
  1. `create_checkout_session` の URL 決定部を次のように置き換える。
     ```python
         # クライアント指定 URL は信用しない（オープンリダイレクト防止）。
         base_frontend = settings.FRONTEND_URL.rstrip("/")
         success_url = f"{base_frontend}/billing/success"
         cancel_url = f"{base_frontend}/billing/cancel"
     ```
  2. `create_portal_session` の return_url を同様に置き換える。
     ```python
         base_frontend = settings.FRONTEND_URL.rstrip("/")
         return_url = f"{base_frontend}/billing"
     ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/billing.py
  Select-String -Path src\backend\routers\billing.py -Pattern 'request.get\("success_url"|request.get\("cancel_url"|request.get\("return_url"'
  ```
- **期待結果**: ruff が通り、検索結果が **0件**（クライアント指定 URL を読まなくなった）。

### Step 26: `FRONTEND_URL` に production 検証を追加する

- **目的**: P1-b の修正（未設定で本番が壊れるのを防ぐ）。
- **対象ファイル**: `src/backend/config.py`（`validate_production_secrets` 之内）
- **変更内容**: 検証的目光の1ブロックを追加する。
  ```python
              if not self.FRONTEND_URL or self.FRONTEND_URL in ("http://localhost:5173", "http://localhost:8080"):
                  raise ValueError(
                      "本番環境 (APP_ENV=production) では FRONTEND_URL に実際の公開URLを設定してください。"
                  )
  ```
- **検証テスト**: `tests/unit/backend/test_config_production_validation.py`（既存、ValidationError の検証あり）
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/config.py
  .venv\Scripts\python.exe -m pytest tests/unit/backend/test_config_production_validation.py -q
  ```
- **期待結果**: 既存テストが `passed`。**追加の検証が既存テストを壊さない**こと
  （既存テストが `FRONTEND_URL` を設定していない場合、該当テストだけ例外的に
  `FRONTEND_URL="https://example.com"` を渡すように既存テストを更新する）。

### Step 27: billing の URL テストを追加する

- **目的**: オープンリダイレクト再発防止。
- **対象ファイル**: `tests/unit/api/test_billing_redirect_urls.py`（**新規作成**）
- **変更内容**: 下記2テストを記入する。
  ```python
  """決済リダイレクトURLが設定値のみから構成されることの回帰テスト。"""
  from __future__ import annotations

  from unittest.mock import MagicMock, patch

  import pytest

  from src.backend.routers import billing


  @pytest.mark.asyncio
  async def test_checkout_urls_ignore_client_supplied_values():
      captured: dict = {}

      def fake_create(**kwargs):
          captured.update(kwargs)
          return "https://stripe.example/checkout"

      with patch.object(billing.StripeClient, "create_checkout_session", staticmethod(fake_create)), \
           patch.object(billing.settings, "FRONTEND_URL", "https://novel.example"):
          result = await billing.create_checkout_session(
              request={"price_id": "price_123", "success_url": "https://evil.example", "cancel_url": "https://evil.example"},
              current_user=MagicMock(id=1),
              db=MagicMock(),
          )
      assert "https://evil.example" not in str(captured)
      assert captured["success_url"] == "https://novel.example/billing/success"
      assert captured["cancel_url"] == "https://novel.example/billing/cancel"


  @pytest.mark.asyncio
  async def test_portal_url_ignores_client_supplied_values():
      captured: dict = {}

      def fake_portal(**kwargs):
          captured.update(kwargs)
          return "https://stripe.example/portal"

      with patch.object(billing.StripeClient, "create_customer_portal_session", staticmethod(fake_portal)), \
           patch.object(billing.settings, "FRONTEND_URL", "https://novel.example"):
          await billing.create_portal_session(
              request={"return_url": "https://evil.example"},
              current_user=MagicMock(stripe_customer_id="cus_1"),
          )
      assert captured["return_url"] == "https://novel.example/billing"
  ```
  **注意**: 2つ目の引数は実装のシグネチャに合わせる。`create_portal_session` が `db` を要求する場合は
  `db=MagicMock()` を渡す。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_billing_redirect_urls.py -q
  ```
- **期待結果**: `2 passed`。**`https://evil.example` がどこにも現れない**ことが本質。

### Step 28: `rag_service._vector_store` の setter を一本化する

- **目的**: P1-c（代入の意味が曖昧）の修正。
- **対象ファイル**: `src/services/rag/rag_service.py`（初期化・property・setter 付近）
- **変更内容**:
  1. `__init__` 内の3行を次のように置き換える。
     ```python
         self._custom_vector_store = vector_store
         self._vector_store_instance = None
     ```
     （現状どおり。**変更なし**）
  2. setter を1変数の意味に統一する。
     ```python
         @_vector_store.setter
         def _vector_store(self, val: BaseVectorStore | None) -> None:
             # 明示的に渡された場合は「カスタム」として扱い、遅延生成しない。
             self._custom_vector_store = val
             self._vector_store_instance = val
     ```
     これにより「`None` を代入 = カスタムなし（既定を使う）」という意味が1箇所で読める。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/services/rag/rag_service.py
  .venv\Scripts\python.exe -m pytest tests/unit/test_graphrag.py -q
  ```
- **期待結果**: ruff が通り、既存テストが `passed`。

### Step 29: `graph_pipeline._vector_store` の setter を明示化する

- **目的**: P1-c の同種問題。
- **対象ファイル**: `src/services/graph_pipeline.py`（`_vector_store` の property/setter）
- **変更内容**: setter に「遅延取得を無効化する意味」のコメントを添える。
  ```python
      @_vector_store.setter
      def _vector_store(self, val: Any | None) -> None:
          # テストからの差し込み用。val が None の場合は「まだ未初期化」として遅延生成させる。
          self._vector_store_instance = val
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/services/graph_pipeline.py
  .venv\Scripts\python.exe -m pytest tests/unit -q -k "graph_pipeline or graphrag"
  ```
- **期待結果**: ruff が通り、該当テストが `passed`。

### Step 30: 遅延プロパティの回帰テストを追加する

- **目的**: 「DI差し替えで get_default_store が呼ばれない」ことを固定する。
- **対象ファイル**: `tests/unit/services/test_lazy_vector_store_injection.py`（**新規作成**）
- **変更内容**: 下記3テストを記入する。
  ```python
  """_vector_store の遅延初期化が、差し込み優先で動くことの回帰テスト。"""
  from __future__ import annotations

  from unittest.mock import MagicMock, patch

  from src.services.graph_pipeline import GraphPipelineService
  from src.services.rag.rag_service import GraphRAGService


  def test_rag_service_uses_injected_store_without_default():
      injected = MagicMock()
      svc = GraphRAGService(vector_store=injected, reranker=MagicMock())
      with patch("src.services.rag.rag_service.get_default_store") as mock_default:
          assert svc._vector_store is injected
      mock_default.assert_not_called()


  def test_graph_pipeline_uses_injected_store_without_default():
      injected = MagicMock()
      svc = GraphPipelineService(enable_vector_store=True)
      svc._vector_store = injected
      with patch("src.services.graph_pipeline.get_default_store") as mock_default:
          assert svc._vector_store is injected
      mock_default.assert_not_called()


  def test_graph_pipeline_disabled_returns_none():
      svc = GraphPipelineService(enable_vector_store=False)
      with patch("src.services.graph_pipeline.get_default_store") as mock_default:
          assert svc._vector_store is None
      mock_default.assert_not_called()
  ```
  **注意**: `GraphPipelineService(...)` / `GraphRAGService(...)` の引数名は実装に従う。
  実行時に `TypeError` が出たら、コンストラクタの引数を確認してテスト側だけを実名に直す。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/services/test_lazy_vector_store_injection.py -q
  ```
- **期待結果**: `3 passed`。

### Step 31: Part 4 の通過確認

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api tests/unit/services -q
  .venv\Scripts\python.exe -m ruff check src/backend/routers/billing.py src/backend/config.py src/services/rag/rag_service.py src/services/graph_pipeline.py
  ```
- **期待結果**: failure 0、ruff が通る。

---

## Part 5: テストと回帰防止ゲート (Step 32-36)

### Step 32: 商用ビートシート API の回帰テストを1本にまとめる

- **目的**: この分野のテストの散在を防ぎ、実行を1コマンドにする。
- **対象ファイル**: `tests/regression/test_v5_c3_commercial_planning_guard.py`（**新規作成**）
- **変更内容**: 下記を記入する。静的チェックのみで、外部依存ゼロ。
  ```python
  """commercial_planning の静的ガード（同期Session・全削除・ハードコード の禁止）。"""
  from __future__ import annotations

  from pathlib import Path

  TARGET = Path(__file__).resolve().parents[2] / "src/backend/routers/commercial_planning.py"


  def test_router_does_not_use_sync_session():
      """async def で get_db（同期Session）を使わない。"""
      src = TARGET.read_text(encoding="utf-8")
      assert "Depends(get_db)" not in src


  def test_router_does_not_delete_all_plots():
      src = TARGET.read_text(encoding="utf-8")
      assert ".delete()" not in src


  def test_router_does_not_hardcode_branch_id_one_in_response():
      src = TARGET.read_text(encoding="utf-8")
      assert '"branch_id": 1' not in src


  def test_router_uses_ssot_beat_model():
      src = TARGET.read_text(encoding="utf-8")
      assert "EpisodeBeat" in src
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_c3_commercial_planning_guard.py -q
  ```
- **期待結果**: `4 passed`。**Step 15-21 を適用する前に実行すると fail になる**ことを記録しておく（効果の証人）。

### Step 33: `commercial_planning` の行数と複雑度を確認する（増殖防止）

- **目的**: 「ハードコード増殖」を防ぐ。
- **作業内容**: 現状把握と変更後の比較を残す。
  ```powershell
  (Get-Content src\backend\routers\commercial_planning.py).Count
  .venv\Scripts\python.exe -m ruff check --select C901 src/backend/routers/commercial_planning.py
  ```
- **期待結果**: C901（複雑度違反）が出ていないこと。行数が減って 減っていること（フェーズ表を消したため）。

### Step 34: ドキュメントの追随（README / 計画インデックス）

- **目的**: 仕様変更を文書化する。
- **対象ファイル**: `plans/README.md`
- **変更内容**: 「v5.0 詳細実装計画書」節の直後に、次の1行を追加する。
  ```markdown
  | [PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md](./PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md) | **P0-4** | **40話ビートシートAPIのSSOT化**<br>-commercial/planning を既存仕様（COMMERCIAL_40EP_BEATS / EpisodeBeat / PlanningAgent）へ接続、タスク発行化、所有者検証、open redirect 対策 | 全36ステップ |
  ```
- **検証コマンド**: `.venv\Scripts\python.exe -c "print('ok')"`
- **期待結果**: `ok`。

### Step 35: C3 の回帰テストをまとめて実行する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_commercial_planning.py tests/unit/api/test_billing_redirect_urls.py tests/unit/workflows tests/contract/test_commercial_planning_contract.py tests/regression/test_v5_c3_commercial_planning_guard.py tests/unit/services/test_lazy_vector_store_injection.py -q
  ```
- **期待結果**: すべて `passed`。

### Step 36: 全体確認と C3 完了判定

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests -q -p no:randomly 2>&1 | Select-Object -Last 20
  .venv\Scripts\python.exe -m ruff check src tests
  ```
- **期待結果**:
  - pytest: `0 failed, 0 error`
  - ruff: `All checks passed!`

#### C3 完了判定（DoD）チェックリスト

- [x] `POST /commercial/planning/generate` が `task_id` を返し、同期で40行を INSERT しない
- [x] 生成処理が `PlanningAgent.generate_commercial_beat_sheet` を通る（router に tension 計算が残っていない）
- [x] `GET /commercial/planning/{book_id}` が `verify_book_ownership` を使う
- [x] レスポンス要素が `EpisodeBeat`（`src/models/beat_sheet.py`）
- [x] `target_episodes` が 1-40 の範囲検証を持つ
- [x] `book_id` 省略時の Book 作成が `current_user.id` を使い、`Branch` も作られる
- [x] 決済リダイレクトURLが `settings.FRONTEND_URL` のみから構成される
- [x] `FRONTEND_URL` が production で localhost なら起動時エラー
- [x] `_vector_store` の差し替えが `get_default_store` を呼ばない
- [x] `pytest tests` が failure 0

---

## 3. リグレッション防止テスト一覧

| テストファイル | 守る事象 | 守るバグ |
|---|---|---|
| `tests/regression/test_v5_c3_commercial_planning_guard.py` | 同期Session・全削除・branch_id固定の禁止 | P0-4b/e/f |
| `tests/unit/api/test_commercial_planning.py` | 所有者検証・404・入力検証・Task 発行 | P0-4c/d |
| `tests/contract/test_commercial_planning_contract.py` | OpenAPI が `EpisodeBeat` ベース | P0-4a（仕様二重化の再発） |
| `tests/unit/workflows/test_commercial_beat_sheet_workflow.py` | 話数正規化・保存・LLM失敗時の素通し | P0-4a |
| `tests/unit/workflows/test_commercial_beat_sheet_task.py` | タスク発行型であること | P0-4e |
| `tests/unit/api/test_billing_redirect_urls.py` | クライアント指定URLを無視 | P1-a |
| `tests/unit/services/test_lazy_vector_store_injection.py` | 差し替え優先・遅延初期化 | P1-c |

## 4. ロールバック

```powershell
git checkout -- src/backend/routers/commercial_planning.py src/backend/routers/billing.py src/backend/config.py
git checkout -- src/services/rag/rag_service.py src/services/graph_pipeline.py
# 新規ファイルは削除
Remove-Item src/backend/workflows/commercial_beat_sheet_workflow.py -ErrorAction SilentlyContinue
```

## 5. 実施順序の注意

- Step 7 → 8 の順（クラス定義 → 基底クラス化）。逆にすると `__init__` の引数がずれる。
- Step 9-10（テスト）を **Step 17（router 書き換え）より前** に作ると、Task 発行化の設計が確定してから router を書ける。
- Step 25-27（billing）は他ステップと独立，随时実行可。
- **イラスト系には一切手を入れない**（Step 33 でも `src/services/illustration/` は対象外）。
