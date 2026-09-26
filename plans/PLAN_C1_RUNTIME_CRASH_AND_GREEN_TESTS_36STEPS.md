# AutoNovel 実装計画書【C1】
# 実行時クラッシュの完全解消とテストスイート緑化（36 Steps）

- **文書ID**: PLAN_C1_RUNTIME_CRASH_AND_GREEN_TESTS_36STEPS
- **作成日**: 2026-09-26
- **対象バージョン**: AutoNovel v5.2.0（v5系 完成形）
- **基準コミット**: `ec728cdc`（feat(v5-finalization)）
- **対象読者**: 小型・低性能LLM（7Bクラス等）。**1ステップ＝1ファイル1変更**に分割し、逐一「検証コマンド → 期待結果」まで自己完結で記述。
- **関連計画書**:
  - [PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md](./PLAN_C2_FORESHADOWING_INTEGRITY_AND_DI_36STEPS.md)
  - [PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md](./PLAN_C3_COMMERCIAL_PLANNING_SSOT_36STEPS.md)

---

## 0. 対象外（重要）

本計画書では **イラスト生成系（画像モデル・画像クライアント・イラストエンジン）は一切扱わない**。
`src/services/illustration/`、`config/image_models.py`、`src/services/illustration/clients/` 配下は
**読み取るだけで変更しない**。イラスト系の整理は別計画で別途実施する。

---

## 1. 目的

コードレビューで確定した次の3系統の不具合を**全て解消し、`pytest tests` が収集エラー0・失敗0で完走する状態**にする。

| 優先度 | 不具合 | 影響 |
|:---:|---|---|
| **P0-1** | `uow.books.get_by_id()` が存在しないため **執筆SSE が必ず `phase:"Error"` を返す** | 主機能が完全死亡 |
| **P0-2** | `self.repo.books.get_by_id()` が `AttributeError` になり **マーケティング生成が必ず失敗** | 同上（テスト無のため未発見） |
| **P0-7** | テストスイートが **収集エラー5件・失敗1件・完走しない** | 「全緑」と言いながら実測結果と異なり、CIを信頼できない |

### 1.1 現状の証拠（実装着手前に必ず再現すること）

```
# 実測（2026-09-26 / Windows / .venv）
.venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing.py -q
→ FAILED  assert 'ContextBuilding' in '... "phase": "Error" ...'
          AttributeError: 'BookRepository' object has no attribute 'get_by_id'

.venv\Scripts\python.exe -m pytest tests/unit/pipeline -q
→ ERROR   ModuleNotFoundError: No module named 'spacy'（5モジュール）
```

---

## 2. 全体構成（36ステップ）

```
[Part 1] Step 1- 6  ベースライン記録・原因確定（コード変更なし）
[Part 2] Step 7-15  P0-1 / P0-2 の実修正
[Part 3] Step16-24  リグレッション防止テストの新設
[Part 4] Step25-32  テスト基盤の是正（spacy / conftest / pytest.ini）
[Part 5] Step33-36  総合緑化・完了判定
```

---

## Part 1: ベースライン記録・原因確定 (Step 1-6)

> **この Part はコードを変更しない。** 後から「何が悪かったか」を説明できる記録を残すのが目的。

### Step 1: 作業開始時のベースラインを採取する

- **目的**: 以降すべてのステップの「 BEFORE / AFTER 」比較の基準を作る。
- **対象ファイル**: なし（結果のみ `docs/v5_c1_baseline.md` に記録）
- **作業内容**:
  1. 次を実行し、出力を `docs/v5_c1_baseline.md` に貼り付ける。
     ```powershell
     .venv\Scripts\python.exe -m pytest tests --collect-only -q 2>&1 | Select-Object -Last 5
     .venv\Scripts\python.exe -m pytest tests/unit -q -p no:randomly 2>&1 | Select-Object -Last 20
     ```
  2. 「収集エラー数 / 失敗数 / 完走したか / 所要時間」を4行で要約して追記する。
- **検証コマンド**: `.venv\Scripts\python.exe -c "print('ok')"`
- **期待結果**: `docs/v5_c1_baseline.md` が作られ、以後比較できる基準値が残る。

### Step 2: `get_by_id` の誤用箇所を全件洗い出す

- **目的**: P0-1/P0-2 以外に同種の誤用がないか確認する。
- **対象ファイル**: なし（結果を `docs/v5_c1_baseline.md` に追記）
- **作業内容**: 次の3コマンドを実行し、出力を記録する。
  ```powershell
  # (a) $'.' ネスト経由の誤用候補
  Select-String -Path src\ -Recurse -Include *.py -Pattern "\.books\.get_by_id|\.chapters\.get_by_id|\.plots\.get_by_id" |
    ForEach-Object { "$($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
  # (b) 単体の get_by_id 定義・呼び出し（正常系との切り分け）
  Select-String -Path src\ -Recurse -Include *.py -Pattern "get_by_id" |
    ForEach-Object { "$($_.Path):$($_.LineNumber)" }
  # (c) 正しい呼び出しの参考
  Select-String -Path src\backend\workflows\*.py -Pattern "self\.repo\.get_" | ForEach-Object { $_.Line.Trim() }
  ```
- **期待結果**: (a) のヒットは **2件のみ**（`stream_writing.py:39` と `marketing_generation_workflow.py:19`）であること。
  (b) のdomainリポジトリ（`novel/episode/character/chapter/branch/plot`）の `get_by_id` は**正常**であり、触らない。

### Step 3: リポジトリの実際のAPIを確定し「規約」を1箇所に書く

- **目的**: 低性能LLMが以後 `get_by_id` を再導入しないよう、唯一の情報源を作る。
- **対象ファイル**: `src/infrastructure/repositories/book.py`
- **変更内容**: クラス `BookRepository` の docstring 冒頭に次の4行を追加する（**新規追加のみ、既存メソッドは触らない**）。
  ```python
  # 作品情報の取得は必ず get_book() を使うこと。
  # get_by_id() は存在しない（过去の実装誤り。詳細は P0-1 / P0-2）。
  # 旧 DataRepositoryFacade 経由で利用する場合は self.repo.get_book(book_id) と書くこと
  # （self.repo.books.get_book(...) は動かない: facade.__getattr__ は coroutine を返すため）。
  ```
- **検証テスト**: なし（ドキュメントのみ）
- **検証コマンド**: `.venv\Scripts\python.exe -m ruff check src/infrastructure/repositories/book.py`
- **期待結果**: ruff が `All checks passed!`。

### Step 4: P0-1 を最小再現して記録する

- **目的**: 「修正前の壊れ方」を1行の証跡として残す。
- **対象ファイル**: なし
- **作業内容**: Step 1 と同じコマンドで `tests/unit/api/test_stream_writing.py` のみを実行し、stderr の `AttributeError: 'BookRepository' object has no attribute 'get_by_id'` を `docs/v5_c1_baseline.md` に追記する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing.py -q 2>&1 | Select-Object -First 20
  ```
- **期待結果**: `FAILED` となり、さらに `get_by_id` の AttributeError が必ず表示される（表示されない場合、Step 2 で見落としがある）。

### Step 5: P0-2 の発生機構を1枚で記録する

- **目的**: `marketing_generation_workflow.py` が**必ず**落ちる理由を、コードで証明する。
- **対象ファイル**: なし
- **作業内容**: 下記を `.venv\Scripts\python.exe` に貼り付けて実行し、出力を記録する。
  ```python
  from src.backend.database.repository import DataRepositoryFacade
  facade = DataRepositoryFacade.__new__(DataRepositoryFacade)   # __init__ を.skip
  attr = facade.books          # __getattr__ が coroutine function を返す
  print(type(attr))            # -> <class 'function'>
  print(hasattr(attr, "get_book"))   # -> False（だから .get_book も .get_by_id も不可）
  ```
- **検証コマンド**: 上記スクリプトを `.venv\Scripts\python.exe` で実行
- **期待結果**: `attr` は function であり `hasattr(attr, "get_book")` が `False`。
  → **正しくは `await self.repo.get_book(book_id)` と直接メソッド呼び出し**が必要だと確定する。

### Step 6: `repo.` 直下呼び出しの「正解パターン」を確定する

- **目的**: 修正時に「どの書き方が既存コードと一致するか」を迷わないようにする。
- **対象ファイル**: なし
- **作業内容**: Step 2(c) の出力から、以下3点が既存スタイルであることを確認して記録する。
  - `illustration_workflow.py:225` → `book = await self.repo.get_book(book_id)`
  - `plot_rebuild_workflow.py:108` → `book = await self.repo.get_book(book_id)`
  - `plot_expansion_workflow.py:21` → `bible = await self.repo.get_latest_bible(book_id)`
- **期待結果**: 「`self.repo.<メソッド名>(...)` のみが正解」という1文が記録に残ること。

---

## Part 2: P0-1 / P0-2 の実修正 (Step 7-15)

### Step 7: 執筆SSE の書籍取得を所有権ガードの戻り値に置き換える

- **目的**: 存在しない `get_by_id` を削除し、**所有者検証の結果を再利用**してクエリを1本減らす。
- **対象ファイル**: `src/backend/routers/stream_writing.py`（36-40行目付近）
- **変更内容**: 現在の
  ```python
          await verify_book_ownership(book_id, user, uow)
          
          # 書籍情報を取得してジャンルを特定
          book = await uow.books.get_by_id(book_id)
          book_genre = getattr(book, "genre", "") or "fantasy"
  ```
  を
  ```python
          # 所有権検証（NotFoundError / 403）を兼ねて Book ORM が返るため、以降は照会不要
          book = await verify_book_ownership(book_id, user, uow)
          book_genre = getattr(book, "genre", "") or "fantasy"
  ```
  に置き換える。**他の行には触らない。**
- **検証テスト**: `tests/unit/api/test_stream_writing.py::test_stream_writing_endpoint`
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing.py -q
  ```
- **期待結果**: ここで **PASS はまだ期待しない**（ローカル `autonovel.db` 依存で落ちる可能性がある。Step 14 でテストを外部依存ゼロにする）。**最低限「`no attribute 'get_by_id'` の AttributeError が出ない」**ことを期待結果とする。

### Step 8: stream_writing.py の行末空白を掃除する

- **目的**: `ruff format` 差分を最小にし、後続ステップの噪声を消す。
- **対象ファイル**: `src/backend/routers/stream_writing.py`
- **変更内容**: 行末に空白のみ残っている行（37行目付近・`verify_book_ownership` の後）を削除する。ロジック変更は禁止。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/stream_writing.py
  .venv\Scripts\python.exe -m ruff format --check src/backend/routers/stream_writing.py
  ```
- **期待結果**: `ruff check` が `All checks passed!`。`ruff format --check` の差分は本計画外の整形差分は残ってよい（Step 12 で整形）。

### Step 9: マーケティング生成ワークフローの書籍取得を修正する

- **目的**: P0-2 を解消する（`AttributeError` → 正しい `get_book` 呼び出し）。
- **対象ファイル**: `src/backend/workflows/marketing_generation_workflow.py`（19行目）
- **変更内容**:
  - 変更前:
    ```python
            book = await self.repo.books.get_by_id(book_id)
    ```
  - 変更後:
    ```python
            # 旧実装の repo.books.get_by_id は存在しない（facade.__getattr__ が coroutine を返すため必ず AttributeError）。
            # 他のワークフローと同じ facade 直下呼び出しに統一する。
            book = await self.repo.get_book(book_id)
    ```
- **検証テスト**: 本ステップ時点では専用テストが無い（Step 18 で作成する）。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/workflows/marketing_generation_workflow.py
  .venv\Scripts\python.exe -c "from src.backend.workflows.marketing_generation_workflow import MarketingGenerationWorkflow; print('import ok')"
  ```
- **期待結果**: `import ok` が出力され、ruff が通る。

### Step 10: 戻り値 None の扱いを他ワークフローに揃える

- **目的**: `get_book` は「見つからない場合 None」を返す。`ValueError` を投げる分岐が既にあることを確認し、他ワークフローの責務と揃える。
- **対象ファイル**: `src/backend/workflows/marketing_generation_workflow.py`（20-21行目）
- **作業内容**: 現状
  ```python
            if not book:
                raise ValueError(f"Book not found: {book_id}")
  ```
  が既に存在することを確認し、**文言のみ** `f"Book not found: {book_id}"` のまま維持する（変更不要なら「変更なし」と記録して次へ）。
- **検証コマンド**: `.venv\Scripts\python.exe -m ruff check src/backend/workflows/marketing_generation_workflow.py`
- **期待結果**: ruff が通る（変更ゼロなら「変更なし」と記録）。

### Step 11: 型注釈を `get_book` の戻り値型に合わせる

- **目的**: mypy が通るようにする。
- **対象ファイル**: `src/backend/workflows/marketing_generation_workflow.py`
- **作業内容**: `book` の使用箇所（`book.title` / `getattr(book, "synopsis", "")`）は DTO でも ORM でも成立する。
  実際の DTO 定義は `src/models/db.py:12`（`class BookDbModel`）と `src/domain/models/book.py:11` の2箇所にある。
  既存 imports の直後に **型注釈用の import のみ** を追加する（ロジックは変更しない）。
  ```python
  from src.models.db import BookDbModel  # 型注釈用（DTO定義: src/models/db.py）
  ```
  続けて `execute` 内の1行に型注釈を付ける。
  ```python
      async def execute(self, reporter: StatusReporter | None = None, **kwargs) -> dict[str, Any]:
          book_id = kwargs["book_id"]
          latest_ep = kwargs["latest_ep"]
          prompt_manager = kwargs.get("prompt_manager")

          # 旧実装の repo.books.get_by_id は存在しないため、facade 直下の get_book を使う。
          book: BookDbModel | None = await self.repo.get_book(book_id)
  ```
- **検証コマンド**:
  ```powershell
  Select-String -Path src\models\db.py -Pattern "class BookDbModel"
  .venv\Scripts\python.exe -m ruff check src/backend/workflows/marketing_generation_workflow.py
  .venv\Scripts\python.exe -m mypy src/backend/workflows/marketing_generation_workflow.py --ignore-missing-imports
  ```
- **期待結果**: 定義位置が1行で出力され、ruff / mypy とも新規エラーなし。

### Step 12: 関数内定義の `MockChapter` をモジュールレベルへ移す

- **目的**: 可読性の改善。SSE 内で定義されている「章が無い場合のプレースホルダ」を独立させる。
- **対象ファイル**: `src/backend/routers/stream_writing.py`
- **変更内容**:
  1. ファイル冒頭（router 定義の直後）に以下を追加する。
     ```python
     class _EmptyChapter:
         """章レコード未作成時のプレースホルダ（書き込み前の暫定オブジェクト）。"""

         def __init__(self, book_id: int, branch_id: int, ep_num: int) -> None:
             self.book_id = book_id
             self.branch_id = branch_id
             self.ep_num = ep_num
             self.title = f"第{ep_num}話"
             self.content = ""
             self.summary = ""
             self.killer_phrase = ""
     ```
  2. 関数内の `class MockChapter: ...` ブロック（46-55行目付近）を削除し、`chapter = _EmptyChapter(book_id, branch_id, ep_num)` の1行に置き換える。
  3. 関数内の外側の `if not chapter:` 条件は**そのまま維持**する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m ruff check src/backend/routers/stream_writing.py
  .venv\Scripts\python.exe -m ruff format src/backend/routers/stream_writing.py
  .venv\Scripts\python.exe -c "from src.backend.routers.stream_writing import _EmptyChapter; print('ok')"
  ```
- **期待結果**: `ok` が出力され、ruff check/format が通る。

### Step 13: 残存 `get_by_id` 誤用がゼロであることを再確認する

- **目的**: Step 9 後に誤用が1件も残っていないことを確認する。
- **作業内容**: Step 2(a) のコマンドを再実行し、結果を記録する。
- **検証コマンド**:
  ```powershell
  Select-String -Path src\ -Recurse -Include *.py -Pattern "\.books\.get_by_id|\.chapters\.get_by_id|\.plots\.get_by_id" |
    ForEach-Object { "$($_.Path):$($_.LineNumber)" }
  ```
- **期待結果**: **出力が空**（0件）。domain リポジトリの `get_by_id` は残ってよい（正規）。

### Step 14: 執筆SSE テストを「外部依存ゼロ」に書き直す

- **目的**: 現状のテストは開発機の `autonovel.db` に `Book(id=1, user_id=1)` があること、および LLM 実行を**暗黙に前提**にしており、他機で落ちる。**偽物は一切使わず、差し替えだけで完結する形**に書き直す。
- **対象ファイル**: `tests/unit/api/test_stream_writing.py`（**全面書き換え**）
- **前提の把握（先に読むこと）**: `src/backend/routers/stream_writing.py` の `_run_writing_pipeline` が使う外部接触は次の3点だけ。
  1. `verify_book_ownership(book_id, user, uow)` … `uow.session` を使う
  2. `uow.chapters.get_chapter(branch_id, ep_num)` / `uow.chapters.create_chapter(...)`
  3. `EpisodeWriter().write(...)` … LLM 呼び出し（失敗しても try/except で握り潰される）
  → この3点を **テスト内で差し替える** だけで、外部DBも LLM も不要になる。
- **変更内容**: ファイル全体を下列の内容に置き換える。
  ```python
  """執筆SSE（GET /api/stream/writing/{book_id}/{ep_num}）の契約テスト。

  方針: DB・LLM に一切依存せず、外部接触3点（所有者検証 / 章リポジトリ / EpisodeWriter）を
  テスト内で差し替える。開発機の autonovel.db が何であっても結果は同じ。
  """
  from __future__ import annotations

  from types import SimpleNamespace
  from unittest.mock import AsyncMock

  import pytest
  from httpx import ASGITransport, AsyncClient

  from src.backend.auth import get_current_user
  from src.backend.routers import stream_writing
  from src.backend.server import app


  class _FakeChapters:
      """uow.chapters の最小スタブ。"""

      def __init__(self) -> None:
          self.created: list[dict] = []

      async def get_chapter(self, branch_id: int, ep_num: int):
          return None  # 章未作成 → プレースホルダ経路を通す

      async def create_chapter(self, **kwargs):
          self.created.append(kwargs)
          return kwargs


  class _FakeUow:
      """UnitOfWork の最小スタブ（async context manager として使う）。"""

      def __init__(self, session=None) -> None:
          self.session = session
          self.chapters = _FakeChapters()

      async def __aenter__(self):
          return self

      async def __aexit__(self, exc_type, exc, tb):
          return False


  class _FakeEpisodeWriter:
      """LLM を呼ばずに執筆結果を返すスタブ。"""

      def __init__(self) -> None:
          pass

      async def write(self, **kwargs):
          return {"text": "テスト本文", "summary": "要約", "killer_phrase": "決め台詞"}


  @pytest.fixture
  def sse_env(monkeypatch):
      """SSE が外部接触しないよう差し替える。"""
      fake_uow = _FakeUow()
      monkeypatch.setattr(stream_writing, "UnitOfWork", lambda db=None: fake_uow)
      monkeypatch.setattr(
          stream_writing,
          "verify_book_ownership",
          AsyncMock(return_value=SimpleNamespace(id=1, user_id=1, genre="fantasy")),
      )
      monkeypatch.setattr(stream_writing, "EpisodeWriter", _FakeEpisodeWriter)
      app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="user")
      yield fake_uow
      app.dependency_overrides.pop(get_current_user, None)


  async def _get_sse(book_id: int = 1, ep_num: int = 1) -> str:
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          resp = await client.get(f"/api/stream/writing/{book_id}/{ep_num}?branch_id=1")
      assert resp.status_code == 200
      assert "text/event-stream" in resp.headers.get("content-type", "")
      return resp.text


  @pytest.mark.asyncio
  async def test_stream_writing_endpoint(sse_env):
      body = await _get_sse()
      assert '"phase": "Error"' not in body
      assert "ContextBuilding" in body
      assert "Complete" in body


  @pytest.mark.asyncio
  async def test_stream_writing_persists_chapter(sse_env):
      await _get_sse()
      assert len(sse_env.chapters.created) == 1
      assert sse_env.chapters.created[0]["content"] == "テスト本文"
  ```
- **検証テスト**: 同ファイル
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing.py -q
  ```
- **期待結果**: `2 passed`。加えて **ローカルDBに依存しない**ことを実地確認する。
  ```powershell
  Move-Item autonovel.db autonovel.db.bak -ErrorAction SilentlyContinue
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing.py -q
  Move-Item autonovel.db.bak autonovel.db -ErrorAction SilentlyContinue
  ```
  `autonovel.db` が無くても `2 passed` であること。

### Step 15: C1-Part2 の通過確認

- **目的**: P0-1/P0-2 の修正が「既存の他テスト」を壊していないことを確認する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api tests/unit/backend tests/unit/domain -q -p no:randomly
  .venv\Scripts\python.exe -m ruff check src/backend/routers/stream_writing.py src/backend/workflows/marketing_generation_workflow.py
  ```
- **期待結果**: 両コマンドとも failure 0、ruff は `All checks passed!`。

---

## Part 3: リグレッション防止テストの新設 (Step 16-24)

> **原則**: 「このバグが再発したら必ず落ちるテスト」を作る。実装の文言ではなく**振る舞い（フェーズ・順序・保存内容）**を固定する。

### Step 16: SSE の契約テストファイルを作成する

- **目的**: フェーズ欠落と Error 混入を恒久的に防ぐ。
- **対象ファイル**: `tests/unit/api/test_stream_writing_contract.py`（**新規作成**）
- **前提（実測済みの phase 名）**: `src/backend/routers/stream_writing.py` が yield する phase は
  `ContextBuilding` → `ContextBuilding` → `Drafting` → `Drafting` → `Auditing` ×3 → `Complete`。
  `"Writing"` という phase 名は**存在しない**ので使用しない。
- **変更内容**: 下記を書き込む。Step 14 の `sse_env` fixture と同じ差し替えを **このファイル内で再定義**する
  （テスト間の暗黙依存を作らないため。共通化は将来課題）。
  ```python
  """執筆SSE の出力契約（フェーズ順序・Error 禁止・進捗単調性）を固定する回帰テスト。"""
  from __future__ import annotations

  import json
  from types import SimpleNamespace
  from unittest.mock import AsyncMock

  import pytest
  from httpx import ASGITransport, AsyncClient

  from src.backend.auth import get_current_user
  from src.backend.routers import stream_writing
  from src.backend.server import app

  PHASE_ORDER = ["ContextBuilding", "Drafting", "Auditing", "Complete"]


  def _events(body: str) -> list[dict]:
      out: list[dict] = []
      for chunk in body.split("data: ")[1:]:
          payload = chunk.split("\n\n")[0]
          try:
              out.append(json.loads(payload))
          except json.JSONDecodeError:
              continue
      return out


  class _FakeChapters:
      async def get_chapter(self, branch_id: int, ep_num: int):
          return None

      async def create_chapter(self, **kwargs):
          return kwargs


  class _FakeUow:
      def __init__(self) -> None:
          self.session = None
          self.chapters = _FakeChapters()

      async def __aenter__(self):
          return self

      async def __aexit__(self, exc_type, exc, tb):
          return False


  class _FakeEpisodeWriter:
      async def write(self, **kwargs):
          return {"text": "本文", "summary": "要約", "killer_phrase": "台詞"}


  @pytest.fixture
  def sse_env(monkeypatch):
      monkeypatch.setattr(stream_writing, "UnitOfWork", lambda db=None: _FakeUow())
      monkeypatch.setattr(
          stream_writing,
          "verify_book_ownership",
          AsyncMock(return_value=SimpleNamespace(id=1, user_id=1, genre="fantasy")),
      )
      monkeypatch.setattr(stream_writing, "EpisodeWriter", _FakeEpisodeWriter)
      app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="user")
      yield
      app.dependency_overrides.pop(get_current_user, None)


  async def _sse_body() -> str:
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          resp = await client.get("/api/stream/writing/1/1?branch_id=1")
      return resp.text


  @pytest.mark.asyncio
  async def test_sse_has_no_error_phase(sse_env):
      assert "Error" not in [e.get("phase") for e in _events(await _sse_body())]


  @pytest.mark.asyncio
  async def test_sse_phase_order_is_stable(sse_env):
      phases = [e.get("phase") for e in _events(await _sse_body())]
      it = iter(phases)
      assert all(any(p == expected for p in it) for expected in PHASE_ORDER)


  @pytest.mark.asyncio
  async def test_sse_progress_is_monotonic(sse_env):
      values = [e.get("progress") for e in _events(await _sse_body())]
      assert values == sorted(values)


  @pytest.mark.asyncio
  async def test_sse_uses_genre_from_verified_book(sse_env):
      """ジャンルが所有者検証で得た Book から渡されていることを確認する。"""
      stream_writing.verify_book_ownership.return_value = SimpleNamespace(  # type: ignore[attr-defined]
          id=1, user_id=1, genre="异世界恋爱"
      )
      captured: dict = {}
      original = _FakeEpisodeWriter.write

      async def _capture(self, **kwargs):
          captured.update(kwargs)
          return await original(self, **kwargs)

      _FakeEpisodeWriter.write = _capture  # type: ignore[method-assign]
      try:
          await _sse_body()
      finally:
          _FakeEpisodeWriter.write = original  # type: ignore[method-assign]

      assert captured["context"]["genre"] == "异世界恋爱"
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing_contract.py -q
  ```
- **期待結果**: `4 passed`。

### Step 17: フェーズ名の実測合わせ（差異があればテスト側定数のみ直す）

- **目的**: `PHASE_ORDER` を「愿望」ではなく「実装の現実」に一致させる。
- **対象ファイル**: `tests/unit/api/test_stream_writing_contract.py`
- **作業内容**: 下記を実行して実 phase 名を出力し、`PHASE_ORDER` が実装と一致するか確認する。
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing_contract.py -q -k "order" -s
  Select-String -Path src\backend\routers\stream_writing.py -Pattern '"phase": "' |
    ForEach-Object { "$($_.LineNumber): $($_.Line.Trim())" }
  ```
  差異がある場合は **テスト側の `PHASE_ORDER` だけ**を実装に合わせる（実装は変更しない）。
- **検証コマンド**: 同上
- **期待結果**: `test_sse_phase_order_is_stable` が `passed`。

### Step 18: マーケティング生成ワークフローの単体テストを作成する

- **目的**: P0-2 の再発防止（テストが存在しなかったことが原因）。
- **対象ファイル**: `tests/unit/workflows/test_marketing_generation_workflow.py`（**新規作成**。ディレクトリが無い場合は作成する）
- **変更内容**: 下記4テストを書き込む。
  ```python
  """MarketingGenerationWorkflow の契約テスト。

  回帰防止: リポジトリの取得は facade 直下の get_book() でなければ AttributeError になる。
  """
  from __future__ import annotations

  from unittest.mock import AsyncMock, MagicMock

  import pytest

  from src.backend.workflows.marketing_generation_workflow import MarketingGenerationWorkflow


  def _make_workflow(book):
      repo = MagicMock()
      # facade と同じ「メソッド直下」API のみ用意する。repo.books 等のネストは存在させない。
      repo.get_book = AsyncMock(return_value=book)
      repo.db = MagicMock()
      marketing = MagicMock()
      marketing.generate_pack = AsyncMock(return_value={"catchcopy": "テスト"})
      return MarketingGenerationWorkflow(repo=repo, marketing=marketing), marketing


  @pytest.mark.asyncio
  async def test_gets_book_via_facade_flat_call():
      book = MagicMock()
      book.title = "タイトル"
      book.synopsis = "あらすじ"
      wf, marketing = _make_workflow(book)
      result = await wf.execute(book_id=1, latest_ep=3)
      assert result == {"catchcopy": "テスト"}
      marketing.generate_pack.assert_awaited_once()


  @pytest.mark.asyncio
  async def test_raises_value_error_when_book_missing():
      wf, _ = _make_workflow(None)
      with pytest.raises(ValueError):
          await wf.execute(book_id=999, latest_ep=1)


  @pytest.mark.asyncio
  async def test_uses_repo_get_book_not_nested_attr():
      """`repo.books.get_by_id` のようなネスト参照を再度使わないことを固定する。"""
      book = MagicMock()
      book.title = "T"
      book.synopsis = "S"
      wf, _ = _make_workflow(book)
      await wf.execute(book_id=1, latest_ep=1)
      wf.repo.get_book.assert_awaited_once_with(1)


  @pytest.mark.asyncio
  async def test_reporter_receives_progress():
      book = MagicMock()
      book.title = "T"
      book.synopsis = "S"
      wf, _ = _make_workflow(book)
      reporter = MagicMock()
      reporter.set_message = MagicMock()
      reporter.add_log = MagicMock()
      await wf.execute(book_id=1, latest_ep=1, reporter=reporter)
      reporter.set_message.assert_called()
  ```
  **注意**: `MarketingGenerationWorkflow.__init__` の引数形は `BaseWorkflow`（`repo=`, `marketing=`）に一致している。Step 18 実行時に `TypeError` が出る場合は `BaseWorkflow.__init__`（`src/backend/workflows/base_workflow.py`）の引数名を確認し、**テスト側のキーワード引数だけを実名に合わせる**。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/workflows/test_marketing_generation_workflow.py -q
  ```
- **期待結果**: `4 passed`。

### Step 19: `DataRepositoryFacade` の契約を固定するテストを追加する

- **目的**: 「facade はメソッド直下呼び出し専用」という未知の前提を、明文化・テスト化する。
- **対象ファイル**: `tests/unit/backend/test_data_repository_facade_contract.py`（**新規作成**）
- **変更内容**: 3テストを書き込む。
  ```python
  """DataRepositoryFacade の契約（メソッド直下呼び出し専用）を固定する。"""
  from __future__ import annotations

  from src.backend.database.repository import DataRepositoryFacade


  def test_getattr_returns_coroutine_function():
      facade = DataRepositoryFacade.__new__(DataRepositoryFacade)
      attr = facade.anything
      assert callable(attr)
      assert attr.__name__ == "wrapper"


  def test_nested_repository_access_is_not_supported():
      """`facade.books.get_book()` は動かない（attr は coroutine function）。"""
      facade = DataRepositoryFacade.__new__(DataRepositoryFacade)
      assert not hasattr(facade.books, "get_book")
      assert not hasattr(facade.books, "get_by_id")


  def test_unknown_attribute_raises_attribute_error():
      facade = DataRepositoryFacade.__new__(DataRepositoryFacade)
      try:
          facade.__getattr__("totally_unknown")
      except AttributeError:
          return
      raise AssertionError("未知の属性では AttributeError が発生すること")
  ```
  最終テストの `raise AssertionError` のメッセージは日本語でよい。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/backend/test_data_repository_facade_contract.py -q
  ```
- **期待結果**: `3 passed`。

### Step 20: 静的スキャンで「誤ったリポジトリ呼び出し」を検出する回帰テストを作る

- **目的**: 新しく誰かが `repo.books.get_by_id(...)` を書いたら、**レビュー前に CI で落ちる**ようにする。
- **対象ファイル**: `tests/regression/test_v5_c1_no_broken_repo_calls.py`（**新規作成**）
- **変更内容**: 下記を書き込む（`src` 配下の `.py` を走査するだけの単純なテスト。AST は使わない＝低性能LLMでも正確に書ける）。
  ```python
  """存在しないリポジトリメソッド呼び出しの静的検出。

  検出するパターン:
    - `.books.get_by_id(` などの、存在しないメソッドの呼び出し
  """
  from __future__ import annotations

  import re
  from pathlib import Path

  REPO_ROOT = Path(__file__).resolve().parents[2]
  SRC = REPO_ROOT / "src"

  FORBIDDEN = [
      re.compile(r"\.books\.get_by_id\("),
      re.compile(r"\.chapters\.get_by_id\("),
      re.compile(r"\.plots\.get_by_id\("),
      re.compile(r"\.characters\.get_by_id\("),
      re.compile(r"\.branches\.get_by_id\("),
  ]

  # domain / infrastructure リポジトリの get_by_id は正規実装なので対象外にする。
  ALLOW_PREFIXES = (
      "src/domain/",
      "src/infrastructure/repositories/",
      "src/application/",
  )


  def test_no_forbidden_repository_calls():
      offenders: list[str] = []
      for path in SRC.rglob("*.py"):
          rel = path.relative_to(REPO_ROOT).as_posix()
          if rel.startswith(ALLOW_PREFIXES):
              continue
          for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
              for pattern in FORBIDDEN:
                  if pattern.search(line):
                      offenders.append(f"{rel}:{i}: {line.strip()}")
      assert not offenders, "存在しないリポジトリメソッドの呼び出しを検出:\n" + "\n".join(offenders)
  ```
  **注意**: `rel` は `src/...` で始まる相対パスになる。`ALLOW_PREFIXES` との比較はそのまま `startswith` でよい。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_c1_no_broken_repo_calls.py -q
  ```
- **期待結果**: `1 passed`。検出0件（=修正が完了している証拠）。

### Step 21: 古いSSEテストの二重登録を削除する

- **目的**: `app.include_router(router)` の重複登録がルートを二重登録し、OpenAPI が壊れるのを防ぐ。
- **対象ファイル**: `tests/unit/api/test_stream_writing.py`（Step 14 で書き換え済み。**書き込み済みの場合は何もしない**）
- **作業内容**: `app.include_router(stream_writing.router)` が残っていれば削除し、Step 14 で書き換えていなければ「Step 14 が未達」と報告して終了する。
- **検証コマンド**: `.venv\Scripts\python.exe -m pytest tests/unit/api/test_stream_writing.py -q`
- **期待結果**: `2 passed`（Step 14 で作成した2件）。

### Step 22: 重複ルート登録の回帰テストを追加する

- **目的**: `server.py` に同じ prefix/パスが二重登録されないことを保証する。
- **対象ファイル**: `tests/regression/test_v5_c1_no_duplicate_routes.py`（**新規作成**）
- **変更内容**:
  ```python
  """FastAPI アプリに同一 (method, path) が重複登録されていないことを保証する。"""
  from __future__ import annotations

  from collections import Counter

  from src.backend.server import app


  def test_no_duplicate_method_path_pairs():
      seen = Counter()
      for route in app.routes:
          methods = getattr(route, "methods", None)
          path = getattr(route, "path", None)
          if not methods or not path:
              continue
          for method in methods:
              seen[(method, path)] += 1
      duplicates = [f"{m} {p} x{c}" for (m, p), c in seen.items() if c > 1]
      assert not duplicates, "重複ルート:\n" + "\n".join(duplicates)
  ```
  **注意**: `src/backend/server.py` の `easy_mode.router` は **3つの prefix で意図的に3回** マウントされる。パスが異なるため重複として検出されない。**検出されたら prefix を同一にする重複バグ**なので、1件ずつ確認する。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_c1_no_duplicate_routes.py -q
  ```
- **期待結果**: `1 passed`。失敗した場合は重複のパスを特定し、`server.py` 側の重複 include を1つだけ削除する。

### Step 23: 回帰テスト3本の通過確認

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_c1_no_broken_repo_calls.py tests/regression/test_v5_c1_no_duplicate_routes.py -q
  ```
- **期待結果**: `2 passed`。

### Step 24: C1-Part3 の通過確認（API 層テストの健全性）

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/api -q -p no:randomly
  ```
- **期待結果**: failure 0。（完走しない場合は `-x` を付けて 1 件ずつ切り分ける。）

---

## Part 4: テスト基盤の是正 (Step 25-32)

### Step 25: `src/pipeline/nlp_init.py` の spacy を遅延 import 化する

- **目的**: spacy 未導入環境で **収集エラー（5件）が起きる**のを根本解決する（skip ではなく、import 自体を失敗させない）。
- **対象ファイル**: `src/pipeline/nlp_init.py`
- **変更内容**:
  1. ファイル冒頭の
     ```python
     import spacy
     from spacy.language import Language
     ```
     を削除する。
  2. 型注釈を文字列表記に置き換える（全3関数共通）。
     - `def get_nlp(model_name: str = "ja_ginza") -> "Language":`
     - `def init_nlp(model_name: str = "ja_ginza") -> "Language":`
     - `def get_nlp_for_testing() -> "Language":`
  3. 各関数の**先頭**に次の import を入れる。
     ```python
         import spacy
         from spacy.language import Language  # noqa: F401
     ```
- **検証テスト**: `tests/unit/pipeline/test_nlp_init.py`
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/pipeline/test_nlp_init.py -q
  ```
- **期待結果**: 収集が成功し、`1 passed`（または既存的环境依存で skip）。**ModuleNotFoundError は出ない。**

### Step 26: `spacy.blank("ja")` も遅延化されていることを確認する

- **対象ファイル**: `src/pipeline/nlp_init.py`（`get_nlp_for_testing`）
- **作業内容**: `nlp = spacy.blank("ja")` が関数内（Step 25 で入れた import の後）にあることを確認する。ModuleLevel に残っていれば関数内へ移す。
- **検証コマンド**: `.venv\Scripts\python.exe -m pytest tests/unit/pipeline -q`
- **期待結果**: `tests/unit/pipeline` 配下で **収集エラー 0**。

### Step 27: pipeline 配下5モジュールの収集エラーを解消確認する

- **対象ファイル**: `tests/unit/pipeline/test_character_extractor.py` ほか4件（変更は原則しない）
- **作業内容**: 収集が通るようになった後、**環境に依存するテストは `pytest.importorskip("spacy")` をモジュール先頭に追加**する。
  ```python
  import pytest
  spacy = pytest.importorskip("spacy")  # spacy 未導入環境ではスキップ
  ```
  これは Step 25 の「遅延 import」で**收集エラーが不要再になった後** nevertheless、环境由来 model（ja_ginza 等）が無い場合の失敗を妥善に skip するため。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/pipeline -q -p no:randomly
  ```
- **期待結果**: `0 errors`。skip を含めて failure 0。

### Step 28: `tests/conftest.py` の `src.agent` エイリアスを削除する

- **目的**: 存在しない `src.agent.*` を `src.agents.*` へ黙って振り替える「偽装」をやめ、真に壊れた import を可視化する。
- **対象ファイル**: `tests/conftest.py`（15-24行目付近）
- **変更内容**: 次のブロックを**丸ごと削除**する。
  ```python
  # ---------------------------------------------------------------------------
  # Legacy import compatibility: `src.agent.*` was purged and unified into
  # `src.agents.*` (Step 16-18), but several test modules still import from
  # `src.agent.*`. Register a module alias so those imports resolve.
  # ---------------------------------------------------------------------------
  try:
      import src.agents as _agents_pkg

      sys.modules.setdefault("src.agent", _agents_pkg)
  except Exception:
      pass
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/agent -q -p no:randomly 2>&1 | Select-Object -Last 15
  ```
- **期待結果**: この時点では **collection error が発生する**（=(alias なしでは壊れる）ことが確認できる）。これが Step 29 の作業対象。

### Step 29: テスト16ファイルの `src.agent.` を `src.agents.` に置換する

- **目的**: エイリアスなしでもテストが通るようにする（正しい修正）。
- **対象ファイル**: 下記の16ファイル（Step 28 で抽出した実ファイル列表を使う）
  ```
  tests/performance/test_cached_archival.py
  tests/integration/api/test_agent_memory_api.py
  tests/integration/agent/memory/test_archival_adapter.py
  tests/unit/agents/test_tool_handler.py
  tests/unit/agent/tools/test_memory_tools.py
  tests/unit/agent/tools/test_consistency.py
  tests/unit/agent/memory/test_working_memory.py
  tests/unit/agent/memory/test_voice_profile.py
  tests/unit/agent/memory/test_manager.py
  tests/unit/agent/memory/test_interfaces.py
  tests/unit/agent/memory/test_initializer.py
  tests/unit/agent/memory/test_core_memory.py
  tests/unit/agent/memory/test_compaction.py
  tests/unit/agent/memory/test_branch_manager.py
  tests/unit/agent/hooks/test_hook_generator.py
  ```
- **作業内容**: 各ファイルで `from src.agent.` → `from src.agents.`、`import src.agent.` → `import src.agents.` に置換する（**文字列分析与 production コードは変更しない**）。
- **検証コマンド**:
  ```powershell
  Select-String -Path tests\ -Recurse -Include *.py -Pattern "src\.agent\." |
    ForEach-Object { "$($_.Path):$($_.LineNumber)" }
  .venv\Scripts\python.exe -m pytest tests/unit/agent tests/unit/agents tests/integration/agent tests/performance -q -p no:randomly
  ```
- **期待結果**: 1つ目のコマンドの**出力が空**。2つ目が failure 0 / error 0（skip  \{\} ぞ\）。

### Step 30: `src/agent` が残っていないことを確認する（ソースコード側の残骸確認）

- **対象ファイル**: なし（確認のみ）
- **作業内容**:
  ```powershell
  Test-Path src\agent
  Select-String -Path src\ -Recurse -Include *.py -Pattern "src\.agent\." |
    ForEach-Object { "$($_.Path):$($_.LineNumber)" }
  ```
- **期待結果**: `Test-Path` が `False`、2つ目の出力が空。
  `True` だった場合、`src/agent` ディレクトリを Step 30 の後半で Step 29 と同じ置換を行い、テスト側を緑にしてから `Remove-Item -Recurse -Force src\agent` する（順序を逆にしない）。

### Step 31: `tests/conftest.py` の環境変数設定をモジュールレベルへ移動する

- **目的**: 現状 `pytest_configure` に書いた `os.environ.setdefault` は **他の import より遅い**ため、`settings.AUTH_DISABLED=False` のまま確定することがある（この計画作成中に実測した）。
- **対象ファイル**: `tests/conftest.py`（30-46行目付近）
- **変更内容**:
  1. ファイル冒頭（`import` 群の**前**、11行目付近の `ROOT = ...` の直前）に次を**追加**する。
     ```python
     # Settings はモジュール import 時に確定するため(pytest_configure は遅すぎる)、
     # 他の import より先にテスト用の既定値を設定する。
     os.environ.setdefault("APP_ENV", "testing")
     os.environ.setdefault("AUTONOVEL_RAG_MODE", "memory")
     os.environ.setdefault("RAG_FALLBACK_MODE", "memory")
     os.environ.setdefault("AUTH_DISABLED", "true")
     ```
  2. `pytest_configure` 内の **同じ4行（`setdefault` 群）は削除**する（重複防止）。`pytest_configure` の `init_db` モンキーパッチ処理は**そのまま残す**。
- **検証テスト**: `tests/test_conftest_fixtures.py`（既存、`AUTH_DISABLED == "true"` を assert している）
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/test_conftest_fixtures.py -q
  .venv\Scripts\python.exe -m pytest tests/unit/test_wizard_flow.py -q
  ```
- **期待結果**: 両方 `passed`。特に `test_wizard_promote_endpoint` が **monkeypatch 無しでも 401 で落ちない**ことを確認する（落ちないことを確認したら、その monkeypatch が冗長なので Step 32 で削除する）。

### Step 32: Step 31 で冗長になった monkeypatch を整理する

- **目的**: テストが「実際の認証設定」に依存するようにし、隠れた依存を減らす。
- **対象ファイル**: `tests/unit/test_wizard_flow.py`（57-59行目付近）
- **作業内容**: Step 31 の実行結果に基づき、
  - **通った場合**: `monkeypatch.setattr(settings, "AUTH_DISABLED", True)` とその import（`from src.backend.config import settings`）を**削除**し、`def test_wizard_promote_endpoint(client):` に戻す。
  - **落ちた場合**: `monkeypatch.setattr(settings, "AUTH_DISABLED", True)` を**残し**、コメントを `# 認証バイパスを明示（tests/conftest.py の環境変数が効かない実行環境向け）` に置き換える。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_wizard_flow.py tests/integration/test_wizard_creation_funnel.py -q
  ```
- **期待結果**: failure 0。

---

## Part 5: 総合緑化・完了判定 (Step 33-36)

### Step 33: `pytest.ini` を整理する

- **目的**: `-p no:debugging`（Python 3.14 pluggy MemoryError の回避）を明示し、`--timeout` を「插件未導入でも落ちない」形にする。
- **対象ファイル**: `pytest.ini`
- **変更内容**:
  1. `addopts` に `--timeout=120` を追加する。
  2. `[pytest]` セクション冒頭に以下のコメントを追加する。
     ```ini
     # -p no:debugging: Python 3.14 + pytest-debugging の pluggy MemoryError 回避（暫定措置）。
     #   恒久対応は pytest-debugging の更新。解除する場合は CI で 1 回だけ確認すること。
     ```
  3. `markers` に `slow` と `integration` を追加する。
     ```ini
     markers =
         perf: Performance benchmark tests
         slow: 長時間を要するテスト
         integration: 外部サービス結合テスト
     ```
  4. ファイル末尾に改行を入れる。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit/test_wizard_flow.py -q
  ```
- **期待結果**: `passed`（`--timeout` 未導入なら Step 34 で導入する）。

### Step 34: `pytest-timeout` を dev 依存として導入する

- **目的**: `--timeout=120` が「未導入だと pytest 自体が起動しない」問題を解消する。
- **対象ファイル**: `pyproject.toml`（`[project.optional-dependencies].dev` または `[dependency-groups].dev`）
- **作業内容**: dev 依存に `pytest-timeout>=2.3.1` を追加し、次を実行する。
  ```powershell
  .venv\Scripts\python.exe -m pip install "pytest-timeout>=2.3.1"
  .venv\Scripts\python.exe -m pytest tests/unit/test_wizard_flow.py -q
  ```
- **期待結果**: `--timeout` を含む `addopts` でも pytest が起動し、テストが `passed`。

### Step 35: `tests/unit` 全体の完走を確認する

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/unit -q -p no:randomly 2>&1 | Select-Object -Last 25
  ```
- **期待結果**: `0 failed, 0 error`。**完走すること**（途中で止まらない）。
  止まる場合は `--timeout=120` のログから特定テストを単独実行し、原因テストを1件ずつ切り分ける（本計画は「完走すること」を完了条件とする）。

### Step 36: 全体テスト・静的検査・C1完了判定

- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests -q -p no:randomly 2>&1 | Select-Object -Last 30
  .venv\Scripts\python.exe -m ruff check src tests
  .venv\Scripts\python.exe -m mypy src/backend/routers/stream_writing.py src/backend/workflows/marketing_generation_workflow.py --ignore-missing-imports
  ```
- **期待結果**:
  - pytest: `0 failed, 0 error`（skip 幽默は可）
  - ruff: `All checks passed!`
  - mypy: 新規エラーなし

#### C1 完了判定（DoD）チェックリスト

- [x] `POST /api/stream/writing/{book_id}/{ep_num}` が `phase:"Error"` を返さない
- [x] `MarketingGenerationWorkflow.execute` が `get_book` 経由で書籍を取得できる
- [x] `tests/unit/pipeline` の収集エラーが 0
- [x] `tests/conftest.py` に `sys.modules["src.agent"]` エイリアスがない
- [x] `src.agent.` / `tests` 内の `src.agent.` 参照が 0 件
- [x] `settings.AUTH_DISABLED` が pytest 中 True で確定する
- [x] 回帰テスト 5 本（`test_v5_c1_no_broken_repo_calls` / `test_v5_c1_no_duplicate_routes` / `test_stream_writing_contract` / `test_marketing_generation_workflow` / `test_data_repository_facade_contract`）が緑
- [x] `pytest tests` が完走し failure 0

---

## 3. リグレッション防止テスト一覧（まとめ）

| テストファイル | 守っている事象 | 守るバグ |
|---|---|---|
| `tests/unit/api/test_stream_writing.py` | SSE がローカルDB非依存で全phaseを流す | P0-1 |
| `tests/unit/api/test_stream_writing_contract.py` | phase順序・Error禁止・progress単調・genre取得元 | P0-1 の再発・仕様漂流 |
| `tests/unit/workflows/test_marketing_generation_workflow.py` | facade直下 `get_book` 呼び出し | P0-2 |
| `tests/unit/backend/test_data_repository_facade_contract.py` | facade はネスト参照不可 | P0-2 の構造的原因 |
| `tests/regression/test_v5_c1_no_broken_repo_calls.py` | 存在しないメソッド呼び出しの静的検出 | P0-1/P0-2 の再発 |
| `tests/regression/test_v5_c1_no_duplicate_routes.py` | (method, path) の重複登録防止 | ルーター二重マウント |
| `tests/unit/pipeline/test_nlp_init.py` | spacy 無しでも import できる | 収集エラー5件 |
| `tests/test_conftest_fixtures.py` | テスト環境が `AUTH_DISABLED=true` | 401 による偽失敗 |

## 4. ロールバック

各ステップは1ファイル完結のため、個別に `git checkout -- <file>` で戻せる。
Part 全体（Step 7-15 / 16-24 / 25-32）を戻す場合は:

```powershell
git diff --name-only ec728cdc
git checkout -- src/backend/routers/stream_writing.py src/backend/workflows/marketing_generation_workflow.py tests/conftest.py pytest.ini
```

## 5. 実施順序の注意

- Step 1-6（記録）を**省略しない**。以後の爭議時に「何が壊れていたか」の唯一の証拠になる。
- Step 7 と Step 9 は**独立**なのでどちらを先にしてもよい。
- Step 28 → 29 → 30 は**必ずこの順**（先に production を直してからテストを移行する）。
- Step 31 は Step 28-30 の**後**に行う（エイリアス撤去後の方が影響が読みやすい）。
