# AutoNovel 実装計画書【C2】
# 伏線データ整合性の修復と DI インフラの健全化（36 Steps）

- **文書ID**: PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS
- **作成日**: 2026-09-26
- **対象バージョン**: AutoNovel v5.2.0（v5系 完成形）
- **基準コミット**: `ec728cdc`（feat(v5-finalization)）の次
- **対象読者**: 小型・低性能LLM（7Bクラス等）。**1ステップ＝1ファイル1変更**に分割し、「検証コマンド → 期待結果」まで自己完結で記述。
- **前提計画書**: [PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md](./PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS.md) を**先に完了**していること（C1 で `pytest tests` が緑になっている状態を前提とする）。
- **関連計画書**: [PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md](./PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md)

---

## 0. 対象外（重要）

- **イラスト生成系は一切扱わない**（`src/services/illustration/`、`config/image_models.py`、`src/services/illustration/clients/`）。
- `commercial_planning` エンドポイントの再設計は **C3** で扱う。本計画書では触らない。

---

## 1. 目的

コードレビューで確定した次の不具合を全て解消する。

| 優先度 | 不具合 | 影響 |
|:---:|---|---|
| **P0-3** | 昇格時の伏線同期が `Plot.detailed_blueprint`（各話ブループリント本文）を「伏線メモ」として読み、**40話分の偽伏線を登録する** | 伏線管理のSSOT崩壊。データ汚染 |
| **P0-3b** | 伏線リポジトリに `ForeshadowingScope` の import が無く、`get_unresolved_by_scope` が `NameError` | スコープ別検索が必ず失敗 |
| **P0-3c** | 昇格同期の重複防止が「1件でもあれば全部スキップ」 | 部分登録時に補完されない |
| **P0-6** | `InfraContainer` から `wiring_config` を外，导致 `InfraContainer` 単体利用時に DI が配線されない | 環境依存の起動失敗 |
| **P0-6b** | `vector_store` が `chroma_client_provider` 依存を失い、**ヘルスチェックと実使用ストアが別物**になり得る | 障害検知の誤り |

---

## 2. 全体構成（36ステップ）

```
[Part 1] Step 1- 6  現状調査（コード変更なし）
[Part 2] Step 7-16  Plot.foreshadowing_notes カラム追加とマイグレーション
[Part 3] Step17-26  伏線同期ロジックの正常化（冪等・スコープ・例外分離）
[Part 4] Step27-32  DI コンテナの修復
[Part 5] Step33-36  統合テストと回帰防止ゲート
```

---

## Part 1: 現状調査 (Step 1-6)

> この Part はコードを変更しない。都以後のステップの判断材料を確定させる。

### Step 1: 伏線データの全流れを1枚に記録する

- **目的**: 「どのカラムが何を意味しているか」を言葉で固定する。
- **作業内容**: 下記を実行し、出力を `docs/v5_c2_baseline.md` に貼り付ける。
  ```powershell
  Select-String -Path src\ -Recurse -Include *.py -Pattern "detailed_blueprint" |
    ForEach-Object { "$($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
  Select-String -Path src\ -Recurse -Include *.py -Pattern "ForeshadowingModel\(" |
    ForEach-Object { "$($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
  ```
- **期待結果**: `detailed_blueprint` の用途が2種類あることを確認できる。
  - `src/backend/routers/plots.py:277` … **ウィザードの伏線メモ**を存放している（本来は設計図のカラム）
  - `src/infrastructure/repositories/plot.py:145` … **各話の設計図本文**を存放している（本来の用途）
  この2つが同じカラムに混在していることが P0-3 の根本原因である。

### Step 2: `detailed_blueprint` の他の利用箇所を確認する

- **作業内容**: Step 1 の出力から、`detailed_blueprint` を**読み書きしている全箇所**を一覧にし、次の3分類に分けて記録する。
  1. 設計図として書き込む（正規）
  2. 伏線メモとして書き込む（誤用。`plots.py:277` の1件のみ）
  3. 読み出して表示するだけ（正規）
- **期待結果**: 誤用が1件だけであると確定すること。1件なら移行コストが小さい。

### Step 3: 既存データの汚染度を測る

- **目的**: 移行が必要かどうかを判断する。
- **作業内容**: 開発DBに対して下記を実行し、件数を記録する。
  ```powershell
  .venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('autonovel.db'); print('foreshadowings:', c.execute('select count(*) from foreshadowings').fetchone()); print(c.execute('select book_id, planted_episode, status, scope, substr(description,1,30) from foreshadowings limit 20').fetchall())"
  ```
- **期待結果**: 件数とサンプルを記録する。0件なら移行スクリプト（Step 25）は「保険」として用意するだけに留める。

### Step 4: `DbForeshadowingRepository` の未実行バグを確認する

- **目的**: P0-3b の存在を証拠で確定する。
- **作業内容**: `src/infrastructure/repositories/foreshadowing_repo.py` を読むと、ファイル冒頭の import は
  `from src.models.foreshadowing_status import ForeshadowingStatus` のみで、
  92行目の `def get_unresolved_by_scope(self, book_id: int, scope: ForeshadowingScope)` は
  **`ForeshadowingScope` が未定義**であることを確認する。実行で証明する。
  ```powershell
  .venv\Scripts\python.exe -c "import inspect; from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository as R; print(R.get_unresolved_by_scope.__annotations__)"
  ```
- **期待結果**: 注解に `ForeshadowingScope` が現れること（未 import なので、実行時は `NameError`）。
  実際は注解は文字列化されるため `NameError` は**呼び出し時**に出る。呼び出し時エラーは Step 22 のテストで固定する。

### Step 5: `UnitOfWork` に伏線リポジトリが無く、export も無いことを確認する

- **作業内容**:
  ```powershell
  Select-String -Path src\backend\database\uow.py -Pattern "foreshadow"
  Select-String -Path src\infrastructure\repositories\__init__.py -Pattern "Foreshadowing"
  Select-String -Path src\backend\database\repositories\__init__.py -Pattern "Foreshadowing"
  ```
- **期待結果**: 3つとも **0件**（= `DbForeshadowingRepository` はどこからも参照されていない）。
  現状 `promotion_service` が生 SQL で `foreshadowings` を直接操作している理由がこれである。

### Step 6: ベースラインとなる伏線関連テストの通過確認

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_v5_foreshadowing_promotion_sync.py tests/unit/services/test_foreshadowing_contract_service.py -q
  ```
- **期待結果**: C1 完了時点で `passed`。これを C2 の BEFORE とする。

---

## Part 2: 専用カラムとマイグレーション (Step 7-16)

### Step 7: `Plot` モデルに `foreshadowing_notes` カラムを追加する

- **目的**: 伏線メモを「設計図」と「別カラム」に分離する（SSOT の一元化）。
- **対象ファイル**: `src/backend/database/models.py`（`class Plot` 内、`detailed_blueprint` の直後）
- **変更内容**: 次の1行を `detailed_blueprint = Column(Text, default="")` の直後に追加する。
  ```python
      # ウィザードビートシート由来の伏線メモ（昇格時に foreshadowings へ同期する）。
      # detailed_blueprint（各話ブループリント本文）とは別物。混用しないこと。
      foreshadowing_notes = Column(Text, default="")
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/database/models.py
  .venv\Scripts\python.exe -c "from src.backend.database.models import Plot; print(Plot.__table__.c.foreshadowing_notes)"
  ```
- **期待結果**: `foreshadowing_notes` の Column 情報が1行で出力される。

### Step 8: 追加したカラムの型を検証する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -c "from src.backend.database.models import Plot; c=Plot.__table__.c.foreshadowing_notes; print(c.type, c.nullable, c.default.arg)"
  ```
- **期待結果**: `TEXT True <text> ...` のように出力され、`default=""` が付いていること。

### Step 9: マイグレーション `0031` のファイルを作成する

- **目的**: 既存DBにカラムを追加する（Alembic の head は `0030_add_foreshadowing_scope`）。
- **対象ファイル**: `src/backend/alembic/versions/0031_add_plot_foreshadowing_notes.py`（**新規作成**）
- **変更内容**: 既存マイグレーション（`0030_add_foreshadowing_scope.py`）の書式に合わせて下記内容で作成する。
  ```python
  """add foreshadowing_notes to plots

  Revision ID: 0031_plot_foreshadowing_notes
  Revises: 0030_add_foreshadowing_scope
  Create Date: 2026-09-26
  """
  from __future__ import annotations

  import sqlalchemy as sa
  from alembic import op

  # revision identifiers, used by Alembic.
  revision = "0031_plot_foreshadowing_notes"
  down_revision = "0030_add_foreshadowing_scope"
  branch_labels = None
  depends_on = None


  def upgrade() -> None:
      op.add_column(
          "plots",
          sa.Column("foreshadowing_notes", sa.Text(), nullable=True, server_default=""),
      )


  def downgrade() -> None:
      op.drop_column("plots", "foreshadowing_notes")
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/alembic/versions/0031_add_plot_foreshadowing_notes.py
  .venv\Scripts\python.exe -m alembic heads
  ```
- **期待結果**: ruff が通り、`alembic heads` が `0031_plot_foreshadowing_notes (head)` を表示する。

### Step 10: マイグレーションのチェーンに重複が無いことを確認する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m alembic history | Select-Object -First 8
  .venv\Scripts\python.exe -m alembic history | Select-String -Pattern "0030_add_foreshadowing_scope"
  ```
- **期待結果**: `0030_add_foreshadowing_scope` が **1回だけ** 出現し、その直後に `0031_plot_foreshadowing_notes` が続く。
  （`0029_add_foreshadowing_scope.py` と `0030_add_foreshadowing_scope.py` は revision ID が異なる別物。混同しないこと。）

### Step 11: 一時DBで `upgrade` / `downgrade` を確認する

- **検証コマンド**:
  ```powershell
  $env:DATABASE_URL = "sqlite:///C:/Users/keide/AppData/Local/Temp/kilo/c2_migration_test.db"
  .venv\Scripts\python.exe -m alembic upgrade head
  .venv\Scripts\python.exe -c "import sqlite3; print([r[1] for r in sqlite3.connect(r'C:\Users\keide\AppData\Local\Temp\kilo\c2_migration_test.db').execute('PRAGMA table_info(plots)')])"
  .venv\Scripts\python.exe -m alembic downgrade -1
  Remove-Item Env:\DATABASE_URL
  Remove-Item C:\Users\keide\AppData\Local\Temp\kilo\c2_migration_test.db -ErrorAction SilentlyContinue
  ```
- **期待結果**: `upgrade` 後に `foreshadowing_notes` が `PRAGMA table_info` に含まれ、`downgrade -1` で消えること。

### Step 12: `PlotRepository.create_or_replace_plot` に引数を追加する

- **目的**: 新しいカラムをリポジトリ経由で書けるようにする。
- **対象ファイル**: `src/infrastructure/repositories/plot.py`
- **変更内容**:
  1. シグネチャの `detailed_blueprint: str,` の**直後**に1行追加する。
     ```python
             foreshadowing_notes: str = "",
     ```
  2. `plot_obj.detailed_blueprint = detailed_blueprint` の**直後**に1行追加する。
     ```python
             plot_obj.foreshadowing_notes = foreshadowing_notes  # type: ignore[assignment]
     ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/infrastructure/repositories/plot.py
  .venv\Scripts\python.exe -c "import inspect; from src.infrastructure.repositories.plot import PlotRepository as P; print('foreshadowing_notes' in inspect.signature(P.create_or_replace_plot).parameters)"
  ```
- **期待結果**: `True` が出力され、ruff が通る。

### Step 13: `UnitOfWorkProtocol` に新引数を反映する

- **対象ファイル**: `src/core/interfaces.py`（`create_or_replace_plot` の宣言は `*args, **kwargs` のため**変更不要**）
- **作業内容**: 既存宣言が `async def create_or_replace_plot(self, *args: Any, **kwargs: Any) -> Any: ...` であることを確認し、「変更不要」と記録して終了する。
- **検証コマンド**: `.venv\Scripts\python.exe -c "from src.core.interfaces import DbPort; print('ok')"`
- **期待結果**: `ok` が出力される。

### Step 14: `wizard_save` の書き込み先を新カラムに変更する

- **目的**: ウィザード保存時に伏線メモを正しいカラムへ入れる。
- **対象ファイル**: `src/backend/routers/plots.py`（271-281行目付近）
- **変更内容**: 変更前
  ```python
                detailed_blueprint=beat.foreshadowing_notes or "",
  ```
  変更後
  ```python
                # detailed_blueprint は各話ブループリント用のカラム。伏線メモは専用カラムへ。
                detailed_blueprint="",
                foreshadowing_notes=beat.foreshadowing_notes or "",
  ```
- **検証テスト**: `tests/integration/test_wizard_creation_funnel.py`（既存）
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/plots.py
  .venv\Scripts\python.exe -m pytest tests/integration/test_wizard_creation_funnel.py -q
  ```
- **期待結果**: ruff が通り、既存テストが `passed`。

### Step 15: 関数内ローカル import をファイル先頭へ移す

- **目的**: リポジトリの一貫性（import は先頭に統一）。
- **対象ファイル**: `src/backend/routers/plots.py`
- **変更内容**:
  1. ファイル先頭の import 群に `from src.backend.database.models_foreshadowing import ForeshadowingModel` を追加する。
  2. 関数内の `from src.backend.database.models_foreshadowing import ForeshadowingModel`（267行目付近）を削除する。
  3. 続けて `src/backend/routers/plots.py` の 297-298 行目の**余分な空行2行**を1行に減らす。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/plots.py
  .venv\Scripts\python.exe -m pytest tests/integration/test_wizard_creation_funnel.py -q
  ```
- **期待結果**: ruff が通り、テストが `passed`。

### Step 16: Part 2 の通過確認

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_v5_foreshadowing_promotion_sync.py tests/integration/test_wizard_creation_funnel.py -q
  .venv\Scripts\python.exe -m ruff check src tests
  ```
- **期待結果**: テストが `passed`、ruff が `All checks passed!`。
  （既存テストが `detailed_blueprint` を前提にしている場合は **Step 19 のテスト更新と同じステップで直す**。）

---

## Part 3: 伏線同期ロジックの正常化 (Step 17-26)

### Step 17: `DbForeshadowingRepository` を infra の `__init__` から export する

- **目的**: `UnitOfWork` から参照できるようにする。
- **対象ファイル**: `src/infrastructure/repositories/__init__.py`
- **変更内容**: まず現状を確認する。
  ```powershell
  Get-Content src\infrastructure\repositories\__init__.py
  ```
  `__all__` に `"DbForeshadowingRepository"` が無ければ、次の2行を追加する。
  ```python
  from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository
  ```
  および `__all__` への `"DbForeshadowingRepository",`。
  既に `import *` 系の再エクスポートになっている場合は、`__all__` への追加だけでよい。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/infrastructure/repositories/__init__.py
  .venv\Scripts\python.exe -c "from src.infrastructure.repositories import DbForeshadowingRepository; print('ok')"
  ```
- **期待結果**: `ok` が出力される。

### Step 18: `UnitOfWork` に `foreshadowings` プロパティを追加する

- **対象ファイル**: `src/backend/database/uow.py`
- **変更内容**:
  1. import 群に `from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository` を追加する。
  2. `def cost(self) -> CostRepository:` プロパティの**直前**に次のプロパティを追加する。
     ```python
         @property
         def foreshadowings(self) -> DbForeshadowingRepository:
             return self._get_repo(DbForeshadowingRepository)
     ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/database/uow.py
  .venv\Scripts\python.exe -c "import asyncio; from src.backend.database.uow import UnitOfWork; print('foreshadowings' in dir(UnitOfWork))"
  ```
- **期待結果**: `True` が出力される。

### Step 19: `DbForeshadowingRepository` に冪等な一括登録メソッドを追加する

- **目的**: 重複登録を防ぎ、既存データを壊さない登録処理を1箇所に集約する。
- **対象ファイル**: `src/infrastructure/repositories/foreshadowing_repo.py`
- **変更内容**: `add` メソッドの**直後**に次のメソッドを追加する。
  ```python
      async def add_if_absent(
          self,
          book_id: int,
          title: str,
          description: str,
          planted_episode: int,
          scope: str = "short_term",
      ) -> Optional[ForeshadowingModel]:
          """同一 (book_id, planted_episode, title) が既にあれば追加しない（冪等な設置）。"""
          existing = await self.db.execute(
              select(ForeshadowingModel)
              .where(ForeshadowingModel.book_id == book_id)
              .where(ForeshadowingModel.planted_episode == planted_episode)
              .where(ForeshadowingModel.title == title)
          )
          if existing.scalar_one_or_none() is not None:
              return None
          record = ForeshadowingModel(
              book_id=book_id,
              title=title,
              description=description,
              planted_episode=planted_episode,
              status=ForeshadowingStatus.PLANTED.value,
              scope=scope,
          )
          self.db.add(record)
          await self.db.flush()
          return record
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/infrastructure/repositories/foreshadowing_repo.py
  ```
- **期待結果**: ruff が `All checks passed!`（`Optional` は既に import 済みのため追加 import 不要）。

### Step 20: `ForeshadowingScope` の未 import を修正する

- **目的**: P0-3b（`NameError`）を解消する。
- **対象ファイル**: `src/infrastructure/repositories/foreshadowing_repo.py`
- **変更内容**: ファイル先頭の import を次のように変更する。
  ```python
  from src.models.foreshadowing_status import ForeshadowingScope, ForeshadowingStatus
  ```
  さらに `get_unresolved_by_scope` の本体を、**文字列でも渡せる**ように次の2行に置き換える。
  ```python
          scope_value = scope.value if isinstance(scope, ForeshadowingScope) else str(scope)
  ```
  ```python
                  ForeshadowingModel.scope == scope_value,
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/infrastructure/repositories/foreshadowing_repo.py
  .venv\Scripts\python.exe -c "from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository; print('import ok')"
  ```
- **期待結果**: ruff が通り、`import ok` が出力される。

### Step 21: スコープ判定を SSOT に基づく関数に集約する

- **目的**: `ep <= 5` という根拠のない魔法数を撤去し、商業構成定義に basing させる。
- **対象ファイル**: `src/config/commercial_beat_sheet.py` の**末尾**（`get_beat_for_episode` の後）
- **変更内容**: 次の関数を追加する。
  ```python
  def get_scope_for_episode(ep_num: int) -> str:
      """指定話数の伏線スコープを商用構成定義から決定する（SSOT: COMMERCIAL_40EP_BEATS）。

      Returns:
          "long_term" または "short_term"
      """
      beat = get_beat_for_episode(ep_num)
      scopes = beat.get("target_scopes") or ["short_term"]
      return "long_term" if "long_term" in scopes else "short_term"
  ```
  さらに `__all__` 相当のエクスポートとして、ファイル末尾に次を追加する（`__all__` があればそこへ）。
  ```python
  __all__ = ["COMMERCIAL_40EP_BEATS", "get_beat_for_episode", "get_scope_for_episode"]
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -c "from src.config.commercial_beat_sheet import get_scope_for_episode as f; print([f(i) for i in (1,5,20,30,35,40)])"
  ```
- **期待結果**: `['short_term', 'short_term', 'short_term', 'short_term', 'long_term', 'short_term']` のように出力される。
  （19-25話・33-38話が `long_term` を含む構成になる）

### Step 22: 新規ユニットテスト: スコープ判定と冪等登録

- **目的**: Step 19-21 で追加したロジックを固定する。
- **対象ファイル**: `tests/unit/services/test_foreshadowing_scope_and_idempotency.py`（**新規作成**）
- **変更内容**: 下記4テストを記入する。
  ```python
  """伏線スコープ判定と冪等登録の回帰テスト。"""
  from __future__ import annotations

  from sqlalchemy import select

  from src.backend.database.models import Book
  from src.backend.database.models_foreshadowing import ForeshadowingModel
  from src.config.commercial_beat_sheet import get_scope_for_episode
  from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository


  def test_scope_comes_from_commercial_beats():
      assert get_scope_for_episode(1) == "short_term"
      assert get_scope_for_episode(20) == "long_term"
      assert get_scope_for_episode(35) == "long_term"
      assert get_scope_for_episode(40) == "short_term"


  async def test_add_if_absent_is_idempotent(real_db_manager):
      session = real_db_manager
      book = Book(title="冪等テスト")
      session.add(book)
      session.commit()

      repo = DbForeshadowingRepository(session)
      first = await repo.add_if_absent(
          book_id=book.id, title="第1話: 伏線A", description="A", planted_episode=1
      )
      assert first is not None
      second = await repo.add_if_absent(
          book_id=book.id, title="第1話: 伏線A", description="A", planted_episode=1
      )
      assert second is None
      session.commit()
      rows = session.execute(
          select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
      ).scalars().all()
      assert len(rows) == 1


  async def test_add_if_absent_allows_different_episodes(real_db_manager):
      session = real_db_manager
      book = Book(title="複数話テスト")
      session.add(book)
      session.commit()
      repo = DbForeshadowingRepository(session)
      for ep in (1, 2, 3):
          created = await repo.add_if_absent(
              book_id=book.id, title=f"第{ep}話: 伏線", description="x", planted_episode=ep
          )
          assert created is not None
      session.commit()
      rows = session.execute(
          select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
      ).scalars().all()
      assert len(rows) == 3


  async def test_get_unresolved_by_scope_accepts_string(real_db_manager):
      session = real_db_manager
      book = Book(title="スコープ検索")
      session.add(book)
      session.commit()
      repo = DbForeshadowingRepository(session)
      await repo.add_if_absent(
          book_id=book.id, title="長期", description="x", planted_episode=20, scope="long_term"
      )
      session.commit()
      found = await repo.get_unresolved_by_scope(book.id, "long_term")
      assert len(found) == 1
  ```
  `asyncio_mode = auto` が `pytest.ini` で有効なため、`@pytest.mark.asyncio` は省略してよい（Step 23 で確認）。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/services/test_foreshadowing_scope_and_idempotency.py -q
  ```
- **期待結果**: `4 passed`。

### Step 23: `promotion_service` の同期を新カラム・冪等	repositories へ書き換える

- **目的**: P0-3 / P0-3c の本修正。
- **対象ファイル**: `src/services/promotion_service.py`（114-147行目付近）
- **変更内容**: 変更前のブロック
  ```python
              if target_b_id is not None:
                  from src.backend.database.models import Plot
                  from src.backend.database.models_foreshadowing import ForeshadowingModel

                  fs_stmt = ForeshadowingModel.__table__.select().where(
                      ForeshadowingModel.book_id == target_b_id
                  )
                  fs_existing = await session.execute(fs_stmt)
                  if fs_existing.first() is None:
                      plot_stmt = (
                          Plot.__table__.select()
                          .where(Plot.book_id == target_b_id)
                          .order_by(Plot.ep_num)
                      )
                      plot_rows = (await session.execute(plot_stmt)).fetchall()
                      for p_row in plot_rows:
                          note = getattr(p_row, "detailed_blueprint", "") or ""
                          if note and note.strip():
                              await session.execute(
                                  ForeshadowingModel.__table__.insert().values(
                                      book_id=target_b_id,
                                      title=f"第{p_row.ep_num}話: {getattr(p_row, 'title', '') or '伏線'}",
                                      description=note.strip(),
                                      planted_episode=p_row.ep_num,
                                      status="planted",
                                      scope="short_term" if p_row.ep_num <= 5 else "long_term",
                                  )
                              )
  ```
  を次の実装に置き換える。
  ```python
              if target_b_id is not None:
                  from src.backend.database.models import Plot
                  from src.infrastructure.repositories.foreshadowing_repo import (
                      DbForeshadowingRepository,
                  )

                  # 伏線メモは専用カラムにだけ入っている。detailed_blueprint は
                  # 各話ブループリント本文なので、絶対に伏線ソースにしないこと。
                  plot_stmt = (
                      Plot.__table__.select()
                      .where(Plot.book_id == target_b_id)
                      .order_by(Plot.ep_num)
                  )
                  plot_rows = (await session.execute(plot_stmt)).fetchall()
                  fs_repo = DbForeshadowingRepository(session)
                  for p_row in plot_rows:
                      note = (getattr(p_row, "foreshadowing_notes", "") or "").strip()
                      if not note:
                          continue
                      ep_num = getattr(p_row, "ep_num", 0) or 0
                      await fs_repo.add_if_absent(
                          book_id=target_b_id,
                          title=f"第{ep_num}話: {getattr(p_row, 'title', '') or '伏線'}",
                          description=note,
                          planted_episode=ep_num,
                          scope=get_scope_for_episode(ep_num),
                      )
  ```
  **重要**: 置換後に `Plot` が未定義にならないよう、ブロック先頭で `from src.backend.database.models import Plot` を
  **必ず import すること**（旧実装のローカル import は置換範囲に含まれるため消える）。
  さらにファイル先頭の import 群（`from src.domain.entities.easy_mode import ...` の付近）に次を追加する。
  ```python
  from src.config.commercial_beat_sheet import get_scope_for_episode
  ```
  `Book` の import は既存のものを流用する（追加不要）。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/services/promotion_service.py
  .venv\Scripts\python.exe -m pytest tests/unit/test_v5_foreshadowing_promotion_sync.py -q
  ```
- **期待結果**: 既存テストが `passed`。ただし既存テストは `detailed_blueprint` に伏線メモを入れており、
  **この変更で 0 件になる**のが正しい挙動。Step 24 でテストを新カラム基準に更新する。

### Step 24: 既存テストを新カラム基準へ更新する

- **目的**: テストが「ブループリント本文は伏線にならない」ことを固定する。
- **対象ファイル**: `tests/unit/test_v5_foreshadowing_promotion_sync.py`
- **変更内容**:
  1. `detailed_blueprint="古びたペンダントの謎（実は王家の紋章）"` を
     `foreshadowing_notes="古びたペンダントの謎（実は王家の紋章）"` に変更する。
  2. `plot2` の `detailed_blueprint=""` を `foreshadowing_notes=""` に変更する。
  3. `plot3` の `detailed_blueprint="謎の行商人が残した合言葉"` を
     `foreshadowing_notes="謎の行商人が残した合言葉"` に変更する。
  4. さらに `plot4`（第4話）を追加し、**`detailed_blueprint` だけ**に設計図本文を持つケースを作る。
     ```python
     plot4 = Plot(
         book_id=book.id,
         branch_id=1,
         ep_num=4,
         title="第4話 設計図のみ",
         detailed_blueprint="これは各話の設計図であり、伏線メモではない。",
         foreshadowing_notes="",
         status="planned",
     )
     ```
     期待値は **2件のまま**（`plot4` のブループリントは登録されないこと）を明示する。
  5. `assert fs_after[1].scope == "short_term"` 相当の検証を追加し、`fs_after[0].scope == "short_term"` を維持する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_v5_foreshadowing_promotion_sync.py -q
  ```
- **期待結果**: `1 passed`。**`plot4` のブループリントが登録されない**ことで P0-3 の本質的回帰防止になる。

### Step 25: 既存データのクリーンアップスクリプトを用意する

- **目的**: 既に誤登録された偽伏線を削除できるようにする（保険）。
- **対象ファイル**: `scripts/cleanup_false_foreshadowings.py`（**新規作成**）
- **変更内容**: 下記を記入する。**既定は dry-run**（`--apply` を付けない限り何も削除しない）。
  ```python
  """誤って detailed_blueprint から作られてしまった伏線を削除する。

  使い方:
      python scripts/cleanup_false_foreshadowings.py            # dry-run（一覧のみ）
      python scripts/cleanup_false_foreshadowings.py --apply    # 実際に削除
  """
  from __future__ import annotations

  import argparse

  from sqlalchemy import create_engine, text

  from src.backend.config import settings

  # 削除対象: 「同じ book_id の Plot.detailed_blueprint と完全一致し、
  # 専用カラム foreshadowing_notes に対応行が無い」planted の伏線のみ。
  SQL_SELECT = """
  SELECT f.id, f.book_id, f.planted_episode, f.description
  FROM foreshadowings f
  WHERE EXISTS (
      SELECT 1 FROM plots p
      WHERE p.book_id = f.book_id
        AND TRIM(p.detailed_blueprint) = TRIM(f.description)
  )
  AND NOT EXISTS (
      SELECT 1 FROM plots p2
      WHERE p2.book_id = f.book_id
        AND p2.planted_episode = f.planted_episode
        AND TRIM(p2.foreshadowing_notes) = TRIM(f.description)
  )
  """


  def main() -> int:
      parser = argparse.ArgumentParser()
      parser.add_argument("--apply", action="store_true", help="実際に削除する（既定は dry-run）")
      args = parser.parse_args()

      engine = create_engine(settings.DATABASE_URL)
      with engine.begin() as conn:
          rows = conn.execute(text(SQL_SELECT)).fetchall()
          print(f"対象: {len(rows)} 件")
          for row in rows:
              print(f"  id={row[0]} book_id={row[1]} ep={row[2]} desc={row[3]!r}")
          if args.apply and rows:
              for row in rows:
                  conn.execute(text("DELETE FROM foreshadowings WHERE id = :id"), {"id": row[0]})
              print(f"{len(rows)} 件を削除しました")
          elif rows:
              print("dry-run のため削除していません（--apply で実行）")
      return 0


  if __name__ == "__main__":
      raise SystemExit(main())
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check scripts/cleanup_false_foreshadowings.py
  .venv\Scripts\python.exe scripts/cleanup_false_foreshadowings.py
  ```
- **期待結果**: ruff が通り、dry-run が「対象: N 件」と一覧を表示して **何も削除しない**。

### Step 26: Part 3 の通過確認

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_v5_foreshadowing_promotion_sync.py tests/unit/services/test_foreshadowing_scope_and_idempotency.py tests/integration/test_wizard_creation_funnel.py -q
  ```
- **期待結果**: すべて `passed`。

---

## Part 4: DI コンテナの修復 (Step 27-32)

### Step 27: 現状の配線状態を記録する

- **目的**: 変更前の挙動を証拠として残す。
- **作業内容**: 下記を実行し、出力を `docs/v5_c2_baseline.md` に追記する。
  ```powershell
  .venv\Scripts\python.exe -c "from src.core.container import InfraContainer, AppContainer; print('Infra wiring:', InfraContainer.wiring_config); print('App wiring:', AppContainer.wiring_config)"
  ```
- **期待結果**: `Infra wiring: None`（配線されない）であることが出力される。

### Step 28: `InfraContainer` に `wiring_config` を復元する

- **目的**: P0-6 の修正（継承したコンテナが配線を失う）。
- **対象ファイル**: `src/core/container/infra.py`
- **変更内容**: `class InfraContainer(containers.DeclarativeContainer):` の直後に次の8行を追加する。
  ```python
      wiring_config = containers.WiringConfiguration(
          modules=[
              "src.services.prompt_version_service",
              "src.services.state_manager",
              "src.backend.database.uow",
          ]
      )
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/core/container/infra.py
  .venv\Scripts\python.exe -c "from src.core.container import InfraContainer; print(InfraContainer.wiring_config is not None)"
  ```
- **期待結果**: `True` が出力される。

### Step 29: `AppContainer` の重複した `wiring_config` を削除する

- **目的**: 定義を1箇所（親クラス）に集約する。
- **対象ファイル**: `src/core/container/app.py`
- **変更内容**: `class AppContainer(InfraContainer):` 直後の `wiring_config` 定義ブロック（8行）を**丸ごと削除**する。
  併せて import の `containers` が未使用になる場合は、`from dependency_injector import providers` のみに直す。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/core/container/app.py
  .venv\Scripts\python.exe -c "from src.core.container import AppContainer; print(AppContainer.wiring_config is not None)"
  ```
- **期待結果**: `True` が出力され、ruff が通る。

### Step 30: `vector_store` を `chroma_client_provider` 依存に戻す

- **目的**: P0-6b の修正（ヘルスチェックと実使用ストアの乖離を解消）。
- **対象ファイル**: `src/core/container/infra.py`
- **変更内容**:
  1. 削除する（Step 30 で置き換える）。
     ```python
     def _get_vector_store():
         from src.services.vector_store import get_default_store
         return get_default_store()
     ```
  2. `chroma_client_provider` の定義を次のとおり **設定値参照** に変更する（ハードコード `./chroma_db` を廃止）。
     ```python
     def _get_chroma_client_provider():
         from src.services.vector_store.chroma import ChromaClientProvider

         from src.backend.config import settings

         return ChromaClientProvider(db_path=settings.CHROMA_DB_PATH)
     ```
  3. `vector_store` の定義を **文字列 provider に戻す**（依存関係を明示するため）。
     ```python
     vector_store: providers.Singleton = providers.Singleton(
         "src.services.vector_store.ChromaVectorStore",
         client_provider=chroma_client_provider,
     )
     ```
     `ChromaClientProvider` / `ChromaVectorStore` は `src/services/vector_store/__init__.py` で
     エクスポート済みのため、文字列指定は解決できる。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/core/container/infra.py
  .venv\Scripts\python.exe -c "from src.core.container import InfraContainer; vs = InfraContainer.vector_store(); print(type(vs).__name__)"
  ```
- **期待結果**: `ChromaVectorStore` が出力される（`InMemoryFallbackStore` や `PgVectorStore` になった場合は、
  `AUTONOVEL_RAG_MODE` の設定を確認して記録する）。

### Step 31: ヘルスチェックと実使用ストアが同一であることをテストする

- **目的**: P0-6b の再発防止。
- **対象ファイル**: `tests/unit/test_container_vector_store_identity.py`（**新規作成**）
- **変更内容**: 下記2テストを記入する。
  ```python
  """DI コンテナの chroma_client_provider / vector_store の同一性を固定する。"""
  from __future__ import annotations

  from src.core.container import InfraContainer


  def test_vector_store_uses_injected_chroma_client_provider():
      """vector_store は注入された chroma_client_provider を保持すること。"""
      InfraContainer.chroma_client_provider.reset()
      InfraContainer.vector_store.reset()
      store = InfraContainer.vector_store()
      provider = InfraContainer.chroma_client_provider()
      assert store.client_provider is provider


  def test_chroma_db_path_is_respected(monkeypatch):
      """ハードコードせず settings.CHROMA_DB_PATH を使うこと。"""
      monkeypatch.setattr("src.backend.config.settings.CHROMA_DB_PATH", "./chroma_db_test_dir")
      InfraContainer.chroma_client_provider.reset()
      provider = InfraContainer.chroma_client_provider()
      assert provider.db_path == "./chroma_db_test_dir"
  ```
  **注意**: 使用する属性名は `src/services/vector_store/chroma.py` の実装に合わせて確定済み。
  `ChromaVectorStore.__init__` は `self.client_provider` を、`ChromaClientProvider.__init__` は `self.db_path` を保持する。
  Step 30 で `vector_store` は **文字列 provider** に戻すため、provider が同一インスタンスとして注入される。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_container_vector_store_identity.py -q
  ```
- **期待結果**: `2 passed`。

### Step 32: `container/__init__.py` の `__getattr__` にコメントを添える

- **目的**: 循環 import を隠している構造の意図と解除条件を明示する。
- **対象ファイル**: `src/core/container/__init__.py`
- **変更内容**: `def __getattr__(name: str):` の直上に次のコメントを追加する（ロジック変更はしない）。
  ```python
  # 遅延 import による循環 import の緩和。
  # 解消条件: app.py が infra.py を import する循環がなくなったとき、
  #           ここを通常のトップレベル import に戻すこと。
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/core/container/__init__.py
  .venv\Scripts\python.exe -c "from src.core.container import AppContainer, LLMGenerateResultProxy; print('ok')"
  ```
- **期待結果**: `ok` が出力される。

---

## Part 5: 統合テストと回帰防止ゲート (Step 33-36)

### Step 33: 昇格フローの統合回帰テストを追加する

- **目的**: 「昇格してもブループリントが伏線にならない」「2回実行しても増えない」を1本に固定する。
- **対象ファイル**: `tests/integration/test_v5_promotion_foreshadowing_integration.py`（**新規作成**）
- **変更内容**: 下記を記入する。昇格の副作用（`Book.mode` 変更）はその場で確認し、DBは `real_db_manager` の使い捨てDBを使う。
  ```python
  """昇格時の伏線同期の統合回帰テスト。

  守ること:
    1) Plot.detailed_blueprint（設計図本文）は伏線として登録されない
    2) Plot.foreshadowing_notes（専用カラム）のみ登録される
    3) 2回昇格しても伏線数は増えない（冪等）
  """
  from __future__ import annotations

  from sqlalchemy import select

  from src.backend.database.models import Book, Plot
  from src.backend.database.models_foreshadowing import ForeshadowingModel
  from src.domain.entities.easy_mode import PromotionRequest
  from src.services.promotion_service import PromotionService


  class _SyncSessionAdapter:
      """PromotionService が期待する async セッションを、同期セッションで代用する。"""

      def __init__(self, sync_session):
          self._s = sync_session

      async def execute(self, statement, *args, **kwargs):
          return self._s.execute(statement, *args, **kwargs)

      async def commit(self):
          self._s.commit()

      async def rollback(self):
          self._s.rollback()

      async def flush(self):
          self._s.flush()

      def add(self, instance):
          self._s.add(instance)


  class _DbManager:
      def __init__(self, session):
          self._adapter = _SyncSessionAdapter(session)

      def get_session(self):
          session = self._adapter

          class _Ctx:
              async def __aenter__(self_inner):
                  return session

              async def __aexit__(self_inner, *args):
                  return False

          return _Ctx()


  async def _make_book_with_plots(session):
      book = Book(title="昇格統合テスト", mode="easy")
      session.add(book)
      session.commit()
      session.add_all([
          Plot(book_id=book.id, branch_id=1, ep_num=1, title="第1話",
               detailed_blueprint="各話の設計図本文", foreshadowing_notes="真の伏線", status="planned"),
          Plot(book_id=book.id, branch_id=1, ep_num=2, title="第2話",
               detailed_blueprint="各話の設計図本文2", foreshadowing_notes="", status="planned"),
      ])
      session.commit()
      return book


  async def test_promotion_syncs_only_foreshadowing_notes(real_db_manager):
      session = real_db_manager
      book = await _make_book_with_plots(session)
      svc = PromotionService(db=_DbManager(session))
      res = await svc.promote_book(PromotionRequest(book_id=str(book.id)))
      assert res.success is True

      rows = session.execute(
          select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
      ).scalars().all()
      assert len(rows) == 1
      assert rows[0].description == "真の伏線"
      assert rows[0].planted_episode == 1


  async def test_promotion_is_idempotent(real_db_manager):
      session = real_db_manager
      book = await _make_book_with_plots(session)
      svc = PromotionService(db=_DbManager(session))
      await svc.promote_book(PromotionRequest(book_id=str(book.id)))
      await svc.promote_book(PromotionRequest(book_id=str(book.id)))
      rows = session.execute(
          select(ForeshadowingModel).where(ForeshadowingModel.book_id == book.id)
      ).scalars().all()
      assert len(rows) == 1
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/integration/test_v5_promotion_foreshadowing_integration.py -q
  ```
- **期待結果**: `2 passed`。**これが P0-3 の本質的な回帰防止テスト**である。

### Step 34: 静的チェックの回帰テスト（ブループリントを伏線ソースに使わない）

- **目的**: `detailed_blueprint` を伏線のソースとして使うコードを、将来も書かないようにする。
- **対象ファイル**: `tests/regression/test_v5_c2_no_blueprint_as_foreshadow_source.py`（**新規作成**）
- **変更内容**: 下記を記入する。文字列マッチではなく **AST で `foreshadowings` 追加時の値来源を検査**するため、表記ゆれで検出をすり抜けない。
  ```python
  """伏線登録コードが detailed_blueprint（設計図本文）を参照していないことを保証する。

  方針: promotion_service.py 内の「ForeshadowingModel / add_if_absent に渡す値」を
  AST で辿り、detailed_blueprint を参照していないことを確認する。
  """
  from __future__ import annotations

  import ast
  from pathlib import Path

  REPO_ROOT = Path(__file__).resolve().parents[2]
  TARGET = REPO_ROOT / "src" / "services" / "promotion_service.py"


  def _called_function_names(node: ast.AST) -> set[str]:
      names: set[str] = set()
      for child in ast.walk(node):
          if not isinstance(child, ast.Call):
              continue
          func = child.func
          if isinstance(func, ast.Attribute):
              names.add(func.attr)
          elif isinstance(func, ast.Name):
              names.add(func.id)
      return names


  def test_promotion_does_not_use_detailed_blueprint_as_foreshadow_source():
      tree = ast.parse(TARGET.read_text(encoding="utf-8"))
      offenders: list[str] = []
      for node in ast.walk(tree):
          if not isinstance(node, ast.Call):
              continue
          if "add_if_absent" not in _called_function_names(node):
              continue
          # 伏線登録呼び出しの引数に detailed_blueprint が現れたら違反
          for arg in list(node.args) + [kw.value for kw in node.keywords]:
              for sub in ast.walk(arg):
                  if isinstance(sub, ast.Attribute) and sub.attr == "detailed_blueprint":
                      offenders.append(f"line {node.lineno}")
                  if isinstance(sub, ast.Constant) and sub.value == "detailed_blueprint":
                      offenders.append(f"line {node.lineno}")
      assert not offenders, "伏線登録が detailed_blueprint を参照しています: " + ", ".join(offenders)


  def test_promotion_reads_only_dedicated_column():
      """専用カラム foreshadowing_notes を参照していることを確認する（逆向きの保証）。"""
      src = TARGET.read_text(encoding="utf-8")
      assert "foreshadowing_notes" in src
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_c2_no_blueprint_as_foreshadow_source.py -q
  ```
- **期待結果**: `2 passed`。Step 23 をまだ適用していない状態で実行すると **1本目が失敗する**（=P0-3 の実在を検出できる）。Step 23 適用後は `passed` になる。

### Step 35: 伏線・DI 関連の回帰テストをまとめて実行する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_v5_foreshadowing_promotion_sync.py tests/unit/services/test_foreshadowing_scope_and_idempotency.py tests/integration/test_v5_promotion_foreshadowing_integration.py tests/regression/test_v5_c2_no_blueprint_as_foreshadow_source.py tests/unit/test_container_vector_store_identity.py -q
  ```
- **期待結果**: すべて `passed`。

### Step 36: 全体確認と C2 完了判定

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests -q -p no:randomly 2>&1 | Select-Object -Last 20
  .venv\Scripts\python.exe -m ruff check src tests scripts
  .venv\Scripts\python.exe -m alembic heads
  ```
- **期待結果**:
  - pytest: `0 failed, 0 error`
  - ruff: `All checks passed!`
  - `alembic heads`: `0031_plot_foreshadowing_notes (head)`

#### C2 完了判定（DoD）チェックリスト

- [x] `Plot.foreshadowing_notes` カラムが存在し、`0031` マイグレーションで既存DBにも追加される
- [x] 昇格時に `detailed_blueprint` の内容が伏線として登録されない
- [x] 昇格を2回行っても伏線数が増えない（冪等）
- [x] スコープは `COMMERCIAL_40EP_BEATS` から決定される（`ep <= 5` の魔法数なし）
- [x] `get_unresolved_by_scope` が `NameError` にならず、文字列でもスコープ指定できる
- [x] `UnitOfWork.foreshadowings` が使える
- [x] `InfraContainer` 単体を import しても DI が配線される
- [x] `vector_store` は `chroma_client_provider` と同じ設定を使う
- [x] `pytest tests` が failure 0

---

## 3. リグレッション防止テスト一覧

| テストファイル | 守る事象 | 守るバグ |
|---|---|---|
| `tests/unit/test_v5_foreshadowing_promotion_sync.py`（更新） | 昇格で専用カラムのみが伏線になる | P0-3 |
| `tests/integration/test_v5_promotion_foreshadowing_integration.py` | 偽伏線ゼロ＋冪等 | P0-3 / P0-3c |
| `tests/regression/test_v5_c2_no_blueprint_as_foreshadow_source.py` | 設計図を伏線ソースにしない | P0-3 の再発 |
| `tests/unit/services/test_foreshadowing_scope_and_idempotency.py` | スコープ判定・冪等登録・スコープ検索 | P0-3b / P0-3c |
| `tests/unit/test_container_vector_store_identity.py` | vector_store と provider の同一性 | P0-6b |
| `tests/integration/test_wizard_creation_funnel.py`（既存） | ウィザード保存が壊れない | 変更の副作用 |

## 4. ロールバック

```powershell
# データ構造（0031）を戻す場合
.venv\Scripts\python.exe -m alembic downgrade -1
# コードはファイル単位で
git checkout -- src/backend/database/models.py src/services/promotion_service.py src/core/container/infra.py
```

## 5. 実施順序の注意

- Step 7（カラム追加）を **必ず Step 9（マイグレーション）より前** に行う。
- Step 23（promotion_service 改修）は Step 22（テスト）の後に行う（先にテストの土台が揃う）。
- Step 28 と Step 29 は必ずこの順（親に復元してから子を消す）。
