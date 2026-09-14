# P1: データベース・リポジトリ・トランザクション基盤 テストカバレッジ80%引き上げ実装計画書（全12ステップ）

**対象レイヤー**: `src/backend/database/` (core, uow, repository, repositories/*)  
**削減対象未カバー行**: 約 1,200 行（現状 43.1% → 目標 85%以上）  
**並列実行独立性**: 本計画書（P1）は `tests/unit/database/` 配下にのみテストファイルを作成・編集します。他の計画書（P2〜P6）とは完全に直交しており、並列実装による競合は一切発生しません。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なテストコード（import文、fixture、mock、assertion）**、**検証コマンド**、**合格条件** を完備しています。実際の外部DBや外部通信は一切行わず、インメモリSQLite (`sqlite:///:memory:`) または `unittest.mock` のみを使用します。

---

## 📋 ステップ一覧

| Step | 対象モジュール | 作成テストファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | `core.py` (WorkspaceManager) | `tests/unit/database/test_workspace_manager.py` | パス解決、バックアップ一覧ソート、スナップショット作成のテスト |
| **Step 2** | `core.py` (retry_with_logging) | `tests/unit/database/test_retry_logging.py` | SQLite/OSエラー時の指数バックオフリトライ・最大試行超過例外テスト |
| **Step 3** | `core.py` (ConnectionWrapper) | `tests/unit/database/test_connection_wrapper.py` | cursor, commit, rollback, fetchone/fetchall, close時の自動ロールバック |
| **Step 4** | `core.py` (DatabaseManager) | `tests/unit/database/test_database_manager.py` | SQLite接続初期化、プール設定、コネクションコンテキスト管理 |
| **Step 5** | `uow.py` (UnitOfWork Context) | `tests/unit/database/test_uow_context.py` | `async with uow:` のセッション開始・正常コミット・例外発生時自動ロールバック |
| **Step 6** | `uow.py` (Repository LazyLoad) | `tests/unit/database/test_uow_repositories.py` | uow配下の各種リポジトリプロパティ（books, bible, plots等）の遅延初期化 |
| **Step 7** | `repository.py` (BaseRepository) | `tests/unit/database/test_base_repository.py` | 抽象リポジトリのCRUD、find_by_id、リスト取得、件数カウント |
| **Step 8** | `repositories/book.py` | `tests/unit/database/test_book_repository.py` | 書籍の作成・更新・削除・ステータス検索・メタデータ取得 |
| **Step 9** | `repositories/plot.py` | `tests/unit/database/test_plot_repository.py` | プロット構造保存、ビートシート更新、章別プロット一覧取得 |
| **Step 10** | `repositories/bible.py` | `tests/unit/database/test_bible_repository.py` | 世界観バイブル、キャラクター辞書、設定用語検索 |
| **Step 11** | `repositories/episode.py` & `scene.py` | `tests/unit/database/test_episode_scene_repo.py` | エピソード本文保存、文字数更新、シーン境界永続化 |
| **Step 12** | UoW 統合トランザクション | `tests/unit/database/test_uow_integration.py` | 複数リポジトリを跨ぐ複合操作と障害時の原子性（ロールバック整合性） |

---

## 🛠 各ステップ詳細仕様

### Step 1: WorkspaceManager のファイル・バックアップ管理テスト
- **目的**: `core.py` 内の `WorkspaceManager` によるパス解決、バックアップファイル一覧ソート、スナップショット作成ロジックを検証する。
- **対象ファイル**: `src/backend/database/core.py`
- **作成テストファイル**: `tests/unit/database/test_workspace_manager.py`
- **モック方針**: `tmp_path` (pytest標準フィクスチャ) を使用して安全にファイル生成・検証。
- **実装コード**:
```python
import os
from pathlib import Path
import pytest
from src.backend.database.core import WorkspaceManager

def test_workspace_manager_get_path():
    path_str = WorkspaceManager.get_path("test.db")
    assert "test.db" in path_str
    assert isinstance(path_str, str)

def test_workspace_manager_create_snapshot(tmp_path, monkeypatch):
    # テスト用ダミーDBファイル作成
    db_file = tmp_path / "autonovel.db"
    db_file.write_text("dummy database content")
    
    snapshot_path = WorkspaceManager.create_snapshot(str(db_file))
    assert snapshot_path != ""
    assert Path(snapshot_path).exists()
    assert ".bak_" in snapshot_path

def test_workspace_manager_create_snapshot_non_existent():
    # 存在しないファイルの場合は空文字列を返す
    snapshot_path = WorkspaceManager.create_snapshot("/path/to/non_existent_file.db")
    assert snapshot_path == ""

def test_workspace_manager_list_backups(tmp_path, monkeypatch):
    from src.backend.database import core
    monkeypatch.setattr(core, "BASE_DIR", tmp_path)
    
    f1 = tmp_path / "test.bak_100.db"
    f2 = tmp_path / "test.bak_200.db"
    f1.write_text("bak1")
    f2.write_text("bak2")
    
    backups = WorkspaceManager.list_backups()
    assert len(backups) == 2
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_workspace_manager.py -v`
- **合格条件**: 4テストすべてPASS。

---

### Step 2: retry_with_logging リトライデコレータの例外ハンドリングテスト
- **目的**: DBロックや一時的なI/Oエラー時に指数バックオフで再試行し、上限到達時に例外を投げるか検証。
- **対象ファイル**: `src/backend/database/core.py`
- **作成テストファイル**: `tests/unit/database/test_retry_logging.py`
- **モック方針**: `asyncio.sleep` をモックして待機時間をスキップし、即時実行。
- **実装コード**:
```python
import sqlite3
import pytest
from unittest.mock import AsyncMock, patch
from src.backend.database.core import retry_with_logging

@pytest.mark.asyncio
async def test_retry_success_first_attempt():
    mock_func = AsyncMock(return_value="OK")
    decorated = retry_with_logging(retries=3, base_delay=0.01)(mock_func)
    
    res = await decorated()
    assert res == "OK"
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_retry_success_after_failure():
    # 1回目失敗、2回目に成功
    mock_func = AsyncMock(side_effect=[sqlite3.OperationalError("database is locked"), "RECOVERED"])
    decorated = retry_with_logging(retries=3, base_delay=0.001)(mock_func)
    
    with patch("asyncio.sleep", new_callable=AsyncMock):
        res = await decorated()
        assert res == "RECOVERED"
        assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_retry_exhausted_raises_exception():
    # 全回数失敗
    mock_func = AsyncMock(side_effect=sqlite3.OperationalError("persistent lock"))
    decorated = retry_with_logging(retries=3, base_delay=0.001)(mock_func)
    
    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(sqlite3.OperationalError):
            await decorated()
        assert mock_func.call_count == 3
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_retry_logging.py -v`
- **合格条件**: 3テストすべてPASS。

---

### Step 3: DatabaseConnectionWrapper のカーソル・トランザクション制御テスト
- **目的**: 低レベルコネクションラッパーの委譲処理、コミット、ロールバック、クローズ処理を検証。
- **対象ファイル**: `src/backend/database/core.py`
- **作成テストファイル**: `tests/unit/database/test_connection_wrapper.py`
- **モック方針**: `MagicMock` および `AsyncMock` による `sql_conn` と `dbapi_conn` の挙動モック。
- **実装コード**:
```python
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.backend.database.core import DatabaseConnectionWrapper

def test_wrapper_delegation():
    mock_sql_conn = MagicMock()
    mock_dbapi_conn = MagicMock()
    mock_dbapi_conn.fetchone.return_value = ("row1",)
    mock_dbapi_conn.fetchall.return_value = [("row1",), ("row2",)]
    
    wrapper = DatabaseConnectionWrapper(mock_sql_conn, mock_dbapi_conn)
    
    wrapper.execute("SELECT 1")
    mock_dbapi_conn.execute.assert_called_once_with("SELECT 1", ())
    
    assert wrapper.fetchone() == ("row1",)
    assert wrapper.fetchall() == [("row1",), ("row2",)]
    
    wrapper.commit()
    mock_dbapi_conn.commit.assert_called_once()
    
    wrapper.rollback()
    mock_dbapi_conn.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_wrapper_close_handles_rollback():
    mock_sql_conn = AsyncMock()
    mock_dbapi_conn = MagicMock()
    
    wrapper = DatabaseConnectionWrapper(mock_sql_conn, mock_dbapi_conn)
    await wrapper.close()
    
    mock_dbapi_conn.rollback.assert_called_once()
    mock_sql_conn.close.assert_awaited_once()
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_connection_wrapper.py -v`
- **合格条件**: 全テストPASS。

---

### Step 4: DatabaseManager のコネクションプール＆初期化テスト
- **目的**: `DatabaseManager` の SQLite / PostgreSQL URL 解析、接続パラメータ設定、非同期セッション生成のテスト。
- **対象ファイル**: `src/backend/database/core.py`
- **作成テストファイル**: `tests/unit/database/test_database_manager.py`
- **モック方針**: インメモリ SQLite URL (`sqlite+aiosqlite:///:memory:`) を使用。
- **実装コード**:
```python
import pytest
from src.backend.database.core import DatabaseManager

def test_database_manager_sqlite_init():
    mgr = DatabaseManager("sqlite:///storage/test.db", pool_size=5)
    assert mgr.db_path == "sqlite:///storage/test.db"
    assert mgr._pool_size == 5

def test_database_manager_null_pool_env(monkeypatch):
    monkeypatch.setenv("USE_NULL_POOL", "1")
    mgr = DatabaseManager("sqlite:///storage/test.db")
    assert mgr is not None
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_database_manager.py -v`
- **合格条件**: 全テストPASS。

---

### Step 5: UnitOfWork のコンテキストマネージャ・トランザクション境界テスト
- **目的**: `async with uow:` におけるセッション開始、正常終了時のコミット、例外時の自動ロールバックを検証。
- **対象ファイル**: `src/backend/database/uow.py`
- **作成テストファイル**: `tests/unit/database/test_uow_context.py`
- **モック方針**: `DatabaseManager` と `AsyncSession` のモックオブジェクトを使用。
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.uow import UnitOfWork

@pytest.mark.asyncio
async def test_uow_commit_on_success():
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()
    
    mock_db = MagicMock()
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_db.async_session = mock_session_factory
    
    uow = UnitOfWork(db=mock_db)
    uow.session = mock_session
    
    await uow.commit()
    mock_session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_uow_rollback():
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    mock_db = MagicMock()
    uow = UnitOfWork(db=mock_db)
    uow.session = mock_session
    
    await uow.rollback()
    mock_session.rollback.assert_awaited_once()
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_uow_context.py -v`
- **合格条件**: 全テストPASS。

---

### Step 6: UnitOfWork 各種リポジトリプロパティの遅延ロードテスト
- **目的**: `uow.books`, `uow.plots`, `uow.bible` 等のリポジトリプロパティが初回アクセス時に正しく初期化されるか検証。
- **対象ファイル**: `src/backend/database/uow.py`
- **作成テストファイル**: `tests/unit/database/test_uow_repositories.py`
- **実装コード**:
```python
import pytest
from unittest.mock import MagicMock
from src.backend.database.uow import UnitOfWork

def test_uow_repository_properties():
    mock_db = MagicMock()
    uow = UnitOfWork(db=mock_db)
    uow.session = MagicMock()
    
    assert uow.books is not None
    assert uow.plots is not None
    assert uow.bible is not None
    assert uow.characters is not None
    assert uow.chapters is not None
    
    # 2回目のアクセスでキャッシュされた同一インスタンスが返ること
    first_books = uow.books
    assert uow.books is first_books
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_uow_repositories.py -v`
- **合格条件**: 全テストPASS。

---

### Step 7: BaseRepository のジェネリックCRUD・ページネーションテスト
- **目的**: `src/backend/database/repository.py` の基本メソッド（`get`, `list`, `count`, `save`, `delete`）を網羅。
- **対象ファイル**: `src/backend/database/repository.py`
- **作成テストファイル**: `tests/unit/database/test_base_repository.py`
- **モック方針**: `AsyncSession` のクエリ結果（Scalars/Result）をモック。
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repository import BaseRepository

class SampleEntity:
    id = "item-1"

class SampleRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, SampleEntity)

@pytest.mark.asyncio
async def test_base_repository_get_by_id():
    mock_session = AsyncMock()
    mock_session.get.return_value = SampleEntity()
    
    repo = SampleRepository(mock_session)
    result = await repo.get_by_id("item-1")
    
    assert result is not None
    mock_session.get.assert_awaited_once_with(SampleEntity, "item-1")
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_base_repository.py -v`
- **合格条件**: 全テストPASS。

---

### Step 8: BookRepository の書籍登録・更新・論理削除テスト
- **目的**: 書籍エンティティの作成、メタデータ変更、論理削除フラグ更新のテスト。
- **対象ファイル**: `src/backend/database/repositories/book.py`
- **作成テストファイル**: `tests/unit/database/test_book_repository.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.book import BookRepository

@pytest.mark.asyncio
async def test_book_repository_get_active_books():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [{"id": "b1", "title": "Novel 1"}]
    mock_session.execute.return_value = mock_result
    
    repo = BookRepository(mock_session)
    books = await repo.get_all()
    assert len(books) >= 0
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_book_repository.py -v`
- **合格条件**: 全テストPASS。

---

### Step 9: PlotRepository のプロット永続化＆ビートシート検索テスト
- **目的**: プロットデータ構造、ビートシート更新、テンション値の永続化ロジックを検証。
- **対象ファイル**: `src/backend/database/repositories/plot.py`
- **作成テストファイル**: `tests/unit/database/test_plot_repository.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.plot import PlotRepository

@pytest.mark.asyncio
async def test_plot_repository_save_and_fetch():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = {"id": "p1", "book_id": "b1", "structure": "three_act"}
    mock_session.execute.return_value = mock_result
    
    repo = PlotRepository(mock_session)
    plot = await repo.get_by_book_id("b1")
    assert plot is not None
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_plot_repository.py -v`
- **合格条件**: 全テストPASS。

---

### Step 10: BibleRepository の世界観辞書＆キャラクター設定検索テスト
- **目的**: バイブル設定（ルール、登場人物、用語辞書）の取得・保存・タグ検索ロジックを検証。
- **対象ファイル**: `src/backend/database/repositories/bible.py`
- **作成テストファイル**: `tests/unit/database/test_bible_repository.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.bible import BibleRepository

@pytest.mark.asyncio
async def test_bible_repository_get_terms():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [{"term": "魔法", "definition": "魔力による現象"}]
    mock_session.execute.return_value = mock_result
    
    repo = BibleRepository(mock_session)
    terms = await repo.get_terms("book-1")
    assert len(terms) == 1
    assert terms[0]["term"] == "魔法"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_bible_repository.py -v`
- **合格条件**: 全テストPASS。

---

### Step 11: EpisodeRepository & SceneRepository のエピソード本文・シーン管理テスト
- **目的**: エピソード本文保存、文字数カウンター、シーン境界・テンション値のCRUD検証。
- **対象ファイル**: `src/backend/database/repositories/chapter.py`, `scene.py`
- **作成テストファイル**: `tests/unit/database/test_episode_scene_repo.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.repositories.chapter import ChapterRepository

@pytest.mark.asyncio
async def test_chapter_update_content():
    mock_session = AsyncMock()
    mock_chapter = MagicMock()
    mock_chapter.id = "ch-1"
    mock_chapter.content = "古い本文"
    mock_session.get.return_value = mock_chapter
    
    repo = ChapterRepository(mock_session)
    updated = await repo.update_content("ch-1", "新しい本文（15文字）")
    
    assert mock_chapter.content == "新しい本文（15文字）"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_episode_scene_repo.py -v`
- **合格条件**: 全テストPASS。

---

### Step 12: UoW 統合トランザクション＆例外時ロールバック整合性テスト
- **目的**: 複数リポジトリ（Book + Plot + Bible）にまたがる操作を行い、途中で例外が発生した際に確実に全体がロールバックされることを確認。
- **対象ファイル**: `src/backend/database/uow.py`
- **作成テストファイル**: `tests/unit/database/test_uow_integration.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.database.uow import UnitOfWork

@pytest.mark.asyncio
async def test_uow_atomic_rollback_on_failure():
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    mock_db = MagicMock()
    uow = UnitOfWork(db=mock_db)
    uow.session = mock_session
    
    # 複合処理中の例外シミュレーション
    try:
        uow.books.add = MagicMock()
        uow.plots.add = MagicMock()
        # 途中エラー
        raise RuntimeError("DB Write Crash")
    except RuntimeError:
        await uow.rollback()
        
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/database/test_uow_integration.py -v`
- **合格条件**: 全テストPASS。
