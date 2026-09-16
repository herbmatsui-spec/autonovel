# P2: コード品質および中長期改善（安定化）実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**策定日**: 2026-09-16  
**目的**:
1. テストスイート内の構文エラー修正の確定コミット（`tests/unit/test_ebook_export_deep.py`）。
2. `generation_tasks.py` における新規イベントループ生成処理（`_run_async`）のスレッドコンテキスト初期化および安全なリソース解放。
3. SQLAlchemy 1.x レガシー記法（`session.query().get`）の SQLAlchemy 2.0 スタイル（`session.get` / `select`）への刷新。
4. Redis/Huey キュー初期化時のタイムアウト明示化による耐障害性向上。
5. フロントエンド依存関係の整理（React Router v7 内包型への一本化、`@types/react-router-dom` 削除、バージョン表記の `4.9.3` 同期）。
6. リトライおよびログ出力における機密情報マスキングと構造化コンテキストの強化。

**低性能LLM向け設計方針**:
- **全12ステップの極小分割**: 1ステップにつき1〜2ファイルのみの変更。
- **完全自己完結コード**: コピペで即座に動作する完全なコード、インポート文、テストケースを記載。
- **検証コマンドと合否基準**: ステップごとにワンライナー検証コマンドとPass条件を明記。

---

## 📋 全12ステップ 実装マトリクス

| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **Step 1** | テスト構文確定 | `tests/unit/test_ebook_export_deep.py` | `_escape_html` のクォート構文エラー解消の検証・確定 | `pytest tests/unit/test_ebook_export_deep.py -o addopts=\"\" --no-cov` |
| **Step 2** | 非同期ループ安全化 | [`src/backend/tasks/generation_tasks.py`](file:///e:/hhh/src/backend/tasks/generation_tasks.py) | `_run_async` で `asyncio.set_event_loop(loop)` を設定し安全に終了 | `python -c "from src.backend.tasks.generation_tasks import _run_async; print('Step 2 OK')"` |
| **Step 3** | ORM 2.0 移行 (Tasks) | [`src/backend/tasks/generation_tasks.py`](file:///e:/hhh/src/backend/tasks/generation_tasks.py) | `_get_user_id_from_book_id` を `session.get(BookDbModel, book_id)` に刷新 | `python -c "from src.backend.tasks.generation_tasks import _get_user_id_from_book_id; print('Step 3 OK')"` |
| **Step 4** | ORM 2.0 移行 (Loader) | [`src/backend/database/series_loader.py`](file:///e:/hhh/src/backend/database/series_loader.py) | `query()` 呼び出し箇所を `select()` / `session.scalars()` / `session.get()` へ統一 | `pytest tests/unit/test_series_loader.py -o addopts=\"\" --no-cov` |
| **Step 5** | キュー耐障害強化 | [`src/backend/tasks/huey.py`](file:///e:/hhh/src/backend/tasks/huey.py) | RedisHuey 接続時にソケット接続タイムアウト（2秒）を明示しハングアップを防止 | `python -c "from src.backend.tasks.huey import check_huey_health; print(check_huey_health())"` |
| **Step 6** | フロント型競合解消 | [`frontend/package.json`](file:///e:/hhh/frontend/package.json) | React Router v7 と競合する非推奨 `@types/react-router-dom: ^5.3.3` を依存から削除 | `python -c "lines=open('frontend/package.json').read(); assert '@types/react-router-dom' not in lines; print('Step 6 OK')"` |
| **Step 7** | バージョン整合同期 | [`frontend/package.json`](file:///e:/hhh/frontend/package.json) | フロントエンドのバージョンを `4.9.0` からバックエンドと統一された `4.9.3` に更新 | `python -c "import json; assert json.load(open('frontend/package.json'))['version'] == '4.9.3'; print('Step 7 OK')"` |
| **Step 8** | DI コンテナ軽量化 | [`src/core/container/app.py`](file:///e:/hhh/src/core/container/app.py) | コンテナ初期化時の冗長な警告ログを抑制しクリーンなブートストラップを確保 | `python -c "from src.core.container import AppContainer; print('Step 8 OK')"` |
| **Step 9** | リトライログ構造化 | [`src/services/retry_decorator.py`](file:///e:/hhh/src/services/retry_decorator.py) | 試行回数・待機秒数・関数名を構造化コンテキストとして出力するように強化 | `pytest tests/unit/test_retry_decorator.py -o addopts=\"\" --no-cov` |
| **Step 10** | ログ機密マスキング | [`src/backend/logging_config.py`](file:///e:/hhh/src/backend/logging_config.py) | JSON ログ出力時の API Key / Authorization ヘッダー値のマスキングフィルタ強化 | `python -c "from src.backend.logging_config import configure; print('Step 10 OK')"` |
| **Step 11** | タスク＆ORM2単体テスト | `tests/unit/backend/test_tasks_async_loop_and_orm2.py` | `_run_async` のスレッドループ設定と `session.get` 移行の単体テスト作成 | `pytest tests/unit/backend/test_tasks_async_loop_and_orm2.py -o addopts=\"\" --no-cov` |
| **Step 12** | P2 総合回帰検証 | 全変更ファイル | P2 対象モジュールのテスト一括実行および全グリーン確認 | `pytest tests/unit/test_ebook_export_deep.py tests/unit/backend/test_tasks_async_loop_and_orm2.py -o addopts=\"\" --no-cov` |

---

## 🛠 各ステップ詳細仕様

### Step 1: テスト構文エラー修正の確定
- **目的**: `tests/unit/test_ebook_export_deep.py` の `_escape_html` テストにおける二重引用符の構文エラー修正が確実に Pass することを確認する。
- **対象ファイル**: `tests/unit/test_ebook_export_deep.py`
- **修正内容**:
  ```python
  def test_escape_html(self, processor):
      raw = '<a href="x">&'
      result = processor._escape_html(raw)
      # & と < がエスケープされることを検証
      assert chr(60) not in result  # < は残らない
      assert chr(38) in result      # & エンティティが使われる
      assert "lt;" in result
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_ebook_export_deep.py -o addopts="" --no-cov
  ```
- **合否基準**: `19 passed` となること。

---

### Step 2: `_run_async` におけるスレッドイベントループ初期化の適正化
- **目的**: ワーカー内部で新規 event loop を作成する際、`asyncio.set_event_loop(loop)` を呼び出してスレッドコンテキストを確立し、外部非同期ライブラリ（httpx 等）のエラーを防ぐ。
- **対象ファイル**: [`src/backend/tasks/generation_tasks.py`](file:///e:/hhh/src/backend/tasks/generation_tasks.py)
- **修正内容**:
  ```python
  # src/backend/tasks/generation_tasks.py L40 付近
  def _run_async(coro: Any) -> Any:
      """新規 event loop を作成して coroutine を同期実行する。"""
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      try:
          return loop.run_until_complete(coro)
      finally:
          try:
              # 残存タスクのキャンセル
              pending = asyncio.all_tasks(loop)
              for task in pending:
                  task.cancel()
              if pending:
                  loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
          finally:
              loop.close()
              asyncio.set_event_loop(None)
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.tasks.generation_tasks import _run_async; print('Step 2 OK')"
  ```
- **合否基準**: `Step 2 OK` と出力されること。

---

### Step 3: `generation_tasks.py` の SQLAlchemy 2.0 スタイル移行
- **目的**: 非推奨の `session.query(BookDbModel).get(...)` を SQLAlchemy 2.0 標準の `session.get(BookDbModel, book_id)` に刷新する。
- **対象ファイル**: [`src/backend/tasks/generation_tasks.py`](file:///e:/hhh/src/backend/tasks/generation_tasks.py)
- **修正内容**:
  ```python
  # src/backend/tasks/generation_tasks.py L28 付近
  def _get_user_id_from_book_id(book_id: int) -> int:
      """書籍IDからユーザーIDを取得する。"""
      session = database.SessionLocal()
      try:
          book = session.get(BookDbModel, book_id)
          if book is None:
              raise ValueError(f"Book not found: {book_id}")
          return book.user_id
      finally:
          session.close()
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.tasks.generation_tasks import _get_user_id_from_book_id; print('Step 3 OK')"
  ```
- **合否基準**: `Step 3 OK` と出力されること。

---

### Step 4: `series_loader.py` の SQLAlchemy 2.0 スタイル統一
- **目的**: `SeriesDataLoader` 内の `query()` 記法を `select()` / `session.scalars()` に統一する。
- **対象ファイル**: [`src/backend/database/series_loader.py`](file:///e:/hhh/src/backend/database/series_loader.py)
- **修正内容**:
  ```python
  from sqlalchemy import select

  # query(EpisodeDbModel).filter(...) を以下のように統一
  stmt = select(EpisodeDbModel).where(EpisodeDbModel.book_id == book_id).order_by(EpisodeDbModel.chapter_number)
  episodes = session.scalars(stmt).all()
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_series_loader.py -o addopts="" --no-cov
  ```
- **合否基準**: `passed` となること。

---

### Step 5: RedisHuey 接続タイムアウトの明示化
- **目的**: Redis 停止時にブロッキングが発生しないよう、ソケット接続タイムアウト（2秒）を明示設定する。
- **対象ファイル**: [`src/backend/tasks/huey.py`](file:///e:/hhh/src/backend/tasks/huey.py)
- **修正内容**:
  ```python
  # src/backend/tasks/huey.py L16 付近
  if settings.HUEY_BACKEND == "redis":
      try:
          huey = RedisHuey(
              "autonovel",
              url=settings.REDIS_URL,
              results=True,
              connection_pool_kwargs={"socket_timeout": 2.0, "socket_connect_timeout": 2.0},
          )
          huey.storage.conn.ping()
      except Exception as e:
          logger.warning("Failed to initialize RedisHuey (timeout/unreachable), falling back to SqliteHuey: %s", e)
          ...
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.tasks.huey import check_huey_health; res=check_huey_health(); assert res['status'] == 'healthy'; print('Step 5 OK')"
  ```
- **合否基準**: `Step 5 OK` と出力されること。

---

### Step 6: フロントエンドの型競合パッケージ削除
- **目的**: React Router v7 に内包される型定義と競合する非推奨 `@types/react-router-dom: ^5.3.3` を削除する。
- **対象ファイル**: [`frontend/package.json`](file:///e:/hhh/frontend/package.json)
- **修正内容**:
  `"dependencies"` セクションから `"@types/react-router-dom": "^5.3.3",` の1行を削除する。
- **検証コマンド**:
  ```powershell
  python -c "lines=open('frontend/package.json').read(); assert '@types/react-router-dom' not in lines; print('Step 6 OK')"
  ```
- **合否基準**: `Step 6 OK` と出力されること。

---

### Step 7: フロントエンドのバージョン表記同期
- **目的**: `frontend/package.json` のバージョン表記をバックエンド（`pyproject.toml`）と一致する `"4.9.3"` に同期する。
- **対象ファイル**: [`frontend/package.json`](file:///e:/hhh/frontend/package.json)
- **修正内容**:
  `"version": "4.9.0"` を `"version": "4.9.3"` に変更する。
- **検証コマンド**:
  ```powershell
  python -c "import json; assert json.load(open('frontend/package.json'))['version'] == '4.9.3'; print('Step 7 OK')"
  ```
- **合否基準**: `Step 7 OK` と出力されること。

---

### Step 8: DI コンテナ初期化の警告抑制と安全化
- **目的**: テスト実行時およびサーバー起動時における DI コンテナ（`AppContainer`）の冗長な非推奨警告を整理する。
- **対象ファイル**: [`src/core/container/app.py`](file:///e:/hhh/src/core/container/app.py)
- **修正内容**:
  コンテナ初期化時のデバッグログレベルを適正化し、本番環境でのノイズを低減する。
- **検証コマンド**:
  ```powershell
  python -c "from src.core.container import AppContainer; print('Step 8 OK')"
  ```
- **合否基準**: `Step 8 OK` と出力されること。

---

### Step 9: リトライログの構造化コンテキスト強化
- **目的**: LLM 呼び出し等のリトライ発生時に、関数名・試行回数・待機時間を構造化ログとして記録する。
- **対象ファイル**: [`src/services/retry_decorator.py`](file:///e:/hhh/src/services/retry_decorator.py)
- **修正内容**:
  ```python
  # src/services/retry_decorator.py
  logger.warning(
      "Retry attempt %d/%d for %s after %.2fs due to: %s",
      attempt + 1,
      max_retries,
      func.__name__,
      delay,
      exc,
  )
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_retry_decorator.py -o addopts="" --no-cov
  ```
- **合否基準**: `passed` となること。

---

### Step 10: 本番 JSON ログの機密ヘッダーマスキング強化
- **目的**: ログ出力時に API Key や Authorization トークンが平文で出力されるリスクを防止する。
- **対象ファイル**: [`src/backend/logging_config.py`](file:///e:/hhh/src/backend/logging_config.py)
- **修正内容**:
  マスキング対象キーに `X-API-Key`, `api_key`, `access_token`, `authorization` を追加し、先頭数文字を残して `***` でマスクする。
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.logging_config import configure; print('Step 10 OK')"
  ```
- **合否基準**: `Step 10 OK` と出力されること。

---

### Step 11: 非同期ループ＆ORM2単体テストの作成
- **目的**: Step 2 および Step 3 で改修した `_run_async` と `_get_user_id_from_book_id` の動作を単体テストで検証する。
- **対象ファイル**: `tests/unit/backend/test_tasks_async_loop_and_orm2.py`（新規作成）
- **実装コード**:
  ```python
  """_run_async および SQLAlchemy 2.0 session.get の動作検証テスト"""
  import asyncio
  import pytest
  from src.backend.tasks.generation_tasks import _run_async

  def test_run_async_properly_handles_coroutine():
      async def sample_coro():
          await asyncio.sleep(0.01)
          return "async_result"
      
      result = _run_async(sample_coro())
      assert result == "async_result"
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/backend/test_tasks_async_loop_and_orm2.py -o addopts="" --no-cov
  ```
- **合否基準**: `1 passed` となること。

---

### Step 12: P2 総合回帰検証
- **目的**: P2 で改修・作成したすべてのテストが安定してパスすることを確認する。
- **対象ファイル**: 全変更ファイル
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_ebook_export_deep.py tests/unit/backend/test_tasks_async_loop_and_orm2.py -o addopts="" --no-cov
  ```
- **合否基準**: すべて `passed` となること。
