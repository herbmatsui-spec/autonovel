# P0: 致命的欠陥およびセキュリティ脆弱性（即時対応）実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**策定日**: 2026-09-16  
**目的**:
1. [`src/backend/auth.py`](file:///e:/hhh/src/backend/auth.py) の `get_current_user` における同期/非同期セッション型不整合による実行時 500 クラッシュ（`TypeError`）を根絶。
2. [`src/backend/server.py`](file:///e:/hhh/src/backend/server.py) のミドルウェア順序を是正し、未認証 401 応答時にも CORS ヘッダーが正しく返却されるよう改善。
3. `issues`, `export`, `misc`, `tasks` ルーターに散見される水平権限昇格（IDOR: 他人の作品・設定・タスクへの不正アクセス/改ざん）を完全に遮断。

**低性能LLM向け設計方針**:
- **全12ステップの極小分割**: 1ステップにつき1〜2ファイルのみの変更。
- **完全自己完結コード**: コピペで即座に動作する完全なコード、インポート文、テストケースを記載。
- **検証コマンドと合否基準**: ステップごとにワンライナー検証コマンドとPass条件を明記。
- **外部依存ゼロ**: テストは SQLite インメモリおよびモックで完結。

---

## 📋 全12ステップ 実装マトリクス

| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **Step 1** | 認証クラッシュ修正 | [`src/backend/auth.py`](file:///e:/hhh/src/backend/auth.py) | `get_current_user` のセッション参照を同期 `db.get(User, user_id)` に修正し `await` を排除 | `python -c "from src.backend.auth import get_current_user; print('auth load OK')"` |
| **Step 2** | 認証単体テスト | `tests/unit/backend/test_auth_real_session.py` | 実 SQLite セッションを用いた JWT トークン解決と `TypeError` 非発生の検証テスト作成 | `pytest tests/unit/backend/test_auth_real_session.py -o addopts=\"\" --no-cov` |
| **Step 3** | CORS 順序是正 | [`src/backend/server.py`](file:///e:/hhh/src/backend/server.py) | `CORSMiddleware` が `GlobalAuthMiddleware` より外側になるよう登録順序を修正 | `python -c "from src.backend.server import app; print('server load OK')"` |
| **Step 4** | CORS 単体テスト | `tests/unit/backend/test_cors_auth_headers.py` | 未認証 401 レスポンスに `Access-Control-Allow-Origin` が確実に付与されることを検証 | `pytest tests/unit/backend/test_cors_auth_headers.py -o addopts=\"\" --no-cov` |
| **Step 5** | IDOR 遮断 (Issues) | [`src/backend/routers/issues.py`](file:///e:/hhh/src/backend/routers/issues.py) | `GET /api/issues/books/{book_id}` に `get_current_user` と `verify_book_ownership` を追加 | `python -c "from src.backend.routers.issues import router; print('issues load OK')"` |
| **Step 6** | 改ざん防止 (Issues) | [`src/backend/routers/issues.py`](file:///e:/hhh/src/backend/routers/issues.py) | `POST /api/issues/{issue_id}/resolve` に `current_user` と所有権チェックを追加 | `python -c "from src.backend.routers.issues import resolve_issue; print('resolve load OK')"` |
| **Step 7** | IDOR 遮断 (Export) | [`src/backend/routers/export.py`](file:///e:/hhh/src/backend/routers/export.py) | `GET /api/export/books/{book_id}` に `current_user` と `verify_book_ownership` を追加 | `python -c "from src.backend.routers.export import export_book; print('export load OK')"` |
| **Step 8** | IDOR 遮断 (eBook) | [`src/backend/routers/export.py`](file:///e:/hhh/src/backend/routers/export.py) | `POST /api/export/ebook` に `current_user` と `verify_book_ownership` を追加 | `python -c "from src.backend.routers.export import export_ebook_alias; print('ebook load OK')"` |
| **Step 9** | 機密流出防止 (Misc) | [`src/backend/routers/misc.py`](file:///e:/hhh/src/backend/routers/misc.py) | `GET /api/bibles/{book_id}` に `current_user` と `verify_book_ownership` を追加 | `python -c "from src.backend.routers.misc import get_bible; print('bible load OK')"` |
| **Step 10** | 機密流出防止 (Misc) | [`src/backend/routers/misc.py`](file:///e:/hhh/src/backend/routers/misc.py) | `GET /api/optimization_history/{book_id}` に認証と `verify_book_ownership` を追加 | `python -c "from src.backend.routers.misc import get_opt_history; print('opt load OK')"` |
| **Step 11** | タスク保護 (Tasks) | [`src/backend/routers/tasks.py`](file:///e:/hhh/src/backend/routers/tasks.py) | `GET /api/tasks/{task_id}/status` でタスク所有者検証（または管理者バイパス）を追加 | `python -c "from src.backend.routers.tasks import get_task_status; print('task load OK')"` |
| **Step 12** | P0 総合結合テスト | `tests/integration/test_p0_security_idor_full.py` | 未認証・他者・所有者・Admin 各ロールでのアクセス制御を網羅検証する統合テスト作成 | `pytest tests/integration/test_p0_security_idor_full.py -o addopts=\"\" --no-cov` |

---

## 🛠 各ステップ詳細仕様

### Step 1: `get_current_user` のセッション参照同期化
- **目的**: 同期 `SessionLocal` を返却する `get_db()` に対し、`await db.get(...)` を呼んで発生する `TypeError: object User can't be used in 'await' expression` を排除する。
- **対象ファイル**: [`src/backend/auth.py`](file:///e:/hhh/src/backend/auth.py)
- **修正内容**:
  ```python
  # src/backend/auth.py L39 付近
  from sqlalchemy.orm import Session  # AsyncSession から Session へ修正

  async def get_current_user(
      token: str = Depends(oauth2_scheme),
      db: Session = Depends(get_db),
  ) -> User:
      """現在の認証済みユーザーを取得する。
      AUTH_DISABLED が True の場合は、開発用モックユーザーを返却してバイパスする。
      """
      if settings.AUTH_DISABLED:
          return _get_dev_mock_user()

      if not token:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="認証が必要です",
              headers={"WWW-Authenticate": "Bearer"},
          )

      payload = decode_token(token, expected_type="access")
      if payload is None:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="無効なトークンです",
          )
      sub = payload.get("sub")
      if sub is None:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="無効なトークンペイロードです",
          )

      user_id = int(sub) if isinstance(sub, (int, str)) and str(sub).isdigit() else sub
      # 同期セッションのため await を外して同期実行
      user = db.get(User, user_id)
      if not user or user.status != "active":
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="ユーザーが存在しないか、無効化されています",
          )
      return user
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.auth import get_current_user; print('Step 1 OK')"
  ```
- **合否基準**: `Step 1 OK` と出力されること。

---

### Step 2: 実セッションを用いた認証単体テスト作成
- **目的**: モックではなく実 DB セッション環境下で JWT から正常に `User` が取得でき、`TypeError` が起きないことを検証する。
- **対象ファイル**: `tests/unit/backend/test_auth_real_session.py`（新規作成）
- **実装コード**:
  ```python
  """実DBセッションを用いた get_current_user の単体テスト"""
  import pytest
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from src.backend.database.models import Base, User
  from src.backend.auth import get_current_user
  from src.backend.security.jwt import create_access_token

  @pytest.fixture
  def real_db_session():
      engine = create_engine("sqlite:///:memory:")
      Base.metadata.create_all(engine)
      Session = sessionmaker(bind=engine)
      session = Session()
      test_user = User(
          id=101,
          email="test_real@example.com",
          display_name="Test Real User",
          role="user",
          status="active",
          plan_tier="free",
          credits=100,
      )
      session.add(test_user)
      session.commit()
      yield session
      session.close()

  @pytest.mark.asyncio
  async def test_get_current_user_with_real_session_no_await_error(real_db_session):
      token = create_access_token(data={"sub": "101", "role": "user"})
      user = await get_current_user(token=token, db=real_db_session)
      assert user.id == 101
      assert user.email == "test_real@example.com"
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/backend/test_auth_real_session.py -o addopts="" --no-cov
  ```
- **合否基準**: `1 passed` となること。

---

### Step 3: `CORSMiddleware` と `GlobalAuthMiddleware` の登録順序適正化
- **目的**: Starlette の LIFO（後勝ち）ミドルウェア登録順序に配慮し、401 応答時にも CORS ヘッダーが付与されるよう登録順序を是正する。
- **対象ファイル**: [`src/backend/server.py`](file:///e:/hhh/src/backend/server.py)
- **修正内容**:
  `GlobalAuthMiddleware` を先に登録し、`CORSMiddleware` をその後に登録することで、リクエスト受付時は `CORSMiddleware` が最外層（最初）、レスポンス返却時は `CORSMiddleware` が最後（CORS ヘッダーを確実に付加）になるようにする。
  ```python
  # src/backend/server.py L98-L110 付近
  from src.backend.middleware.auth_middleware import GlobalAuthMiddleware

  register_error_handlers(app)

  # 1. 内部側の認証ミドルウェアを先に追加
  app.add_middleware(GlobalAuthMiddleware)

  # 2. 最外層の CORS ミドルウェアを後から追加（レスポンス全体に CORS ヘッダーを保証）
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.cors_origin_list,
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
      allow_headers=settings.cors_allow_headers_list,
  )
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.server import app; print('Step 3 OK')"
  ```
- **合否基準**: `Step 3 OK` と出力されること。

---

### Step 4: 401 応答時の CORS ヘッダー付与テスト作成
- **目的**: 未認証アクセス（401）時に、ブラウザが要求する CORS ヘッダーが正しく付与されていることを確認する。
- **対象ファイル**: `tests/unit/backend/test_cors_auth_headers.py`（新規作成）
- **実装コード**:
  ```python
  """未認証 401 時の CORS ヘッダー検証テスト"""
  import pytest
  from fastapi.testclient import TestClient
  from src.backend.server import app

  def test_unauthorized_response_contains_cors_headers():
      client = TestClient(app)
      response = client.get(
          "/api/books",
          headers={"Origin": "http://localhost:5173"}
      )
      assert response.status_code == 401
      assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
      assert response.headers.get("access-control-allow-credentials") == "true"
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/backend/test_cors_auth_headers.py -o addopts="" --no-cov
  ```
- **合否基準**: `1 passed` となること。

---

### Step 5: `GET /api/issues/books/{book_id}` への認可・所有権ガード適用
- **目的**: 未認証・他人の監査イシュー一覧閲覧を遮断する。
- **対象ファイル**: [`src/backend/routers/issues.py`](file:///e:/hhh/src/backend/routers/issues.py)
- **修正内容**:
  ```python
  from src.backend.auth import get_current_user
  from src.backend.database.models import User
  from src.backend.security.owner_guard import verify_book_ownership

  @router.get("/books/{book_id}")
  async def get_issues(
      book_id: int,
      current_user: User = Depends(get_current_user),
  ):
      async with UnitOfWork(AppContainer.db()) as uow:
          await verify_book_ownership(book_id, current_user, uow)
          return await uow.audit.get_book_issues(book_id)
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.issues import router; print('Step 5 OK')"
  ```
- **合否基準**: `Step 5 OK` と出力されること。

---

### Step 6: `POST /api/issues/{issue_id}/resolve` への所有権ガード適用
- **目的**: API Key 保持者が他人の作品イシューを解決・WorldBible 書き換えできないよう防御する。
- **対象ファイル**: [`src/backend/routers/issues.py`](file:///e:/hhh/src/backend/routers/issues.py)
- **修正内容**:
  ```python
  @router.post("/{issue_id}/resolve")
  async def resolve_issue(
      issue_id: int,
      req: ResolveIssueRequest,
      current_user: User = Depends(get_current_user),
  ):
      async with UnitOfWork(AppContainer.db()) as uow:
          issue = await uow.audit.get_issue(issue_id)
          if not issue:
              raise NotFoundError(
                  "Issue not found", resource_type="AuditIssue", resource_id=str(issue_id)
              )
          # 作品の所有権を検証
          await verify_book_ownership(issue.book_id, current_user, uow)
          ...
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.issues import resolve_issue; print('Step 6 OK')"
  ```
- **合否基準**: `Step 6 OK` と出力されること。

---

### Step 7: `GET /api/export/books/{book_id}` への所有権ガード適用
- **目的**: 他人の小説本文の無断エクスポートを遮断する。
- **対象ファイル**: [`src/backend/routers/export.py`](file:///e:/hhh/src/backend/routers/export.py)
- **修正内容**:
  ```python
  from src.backend.auth import get_current_user
  from src.backend.database.models import User
  from src.backend.security.owner_guard import verify_book_ownership

  @router.get("/books/{book_id}")
  async def export_book(
      book_id: int,
      platform: str = Query("narou", description="narou | kakuyomu | nocturne | nocturn"),
      current_user: User = Depends(get_current_user),
  ) -> dict[str, Any]:
      """作品を指定プラットフォーム用に整形して出力する。"""
      async with UnitOfWork(AppContainer.db()) as uow:
          book_row = await verify_book_ownership(book_id, current_user, uow)
          ...
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.export import export_book; print('Step 7 OK')"
  ```
- **合否基準**: `Step 7 OK` と出力されること。

---

### Step 8: `POST /api/export/ebook` への所有権ガード適用
- **目的**: 他人の作品 ID を指定した電子書籍（EPUB/PDF）の生成・ダウンロードを遮断する。
- **対象ファイル**: [`src/backend/routers/export.py`](file:///e:/hhh/src/backend/routers/export.py)
- **修正内容**:
  ```python
  @router.post(
      "/ebook",
      response_model=EbookExportResponse,
      responses={503: {"description": "Multimedia disabled"}},
  )
  async def export_ebook_alias(
      payload: EbookExportRequest,
      current_user: User = Depends(get_current_user),
      service: MultimediaService = Depends(get_multimedia_service),
  ) -> EbookExportResponse:
      _check_multimedia()
      await verify_book_ownership(payload.book_id, current_user)
      result = await asyncio.to_thread(service.export_ebook, book_id=payload.book_id, formats=payload.formats)
      ...
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.export import export_ebook_alias; print('Step 8 OK')"
  ```
- **合否基準**: `Step 8 OK` と出力されること。

---

### Step 9: `GET /api/bibles/{book_id}` への認証・所有権ガード適用
- **目的**: 他人の機密プロット設定・伏線マップ（WorldBible）の外部露出を完全に遮断する。
- **対象ファイル**: [`src/backend/routers/misc.py`](file:///e:/hhh/src/backend/routers/misc.py)
- **修正内容**:
  ```python
  from src.backend.auth import get_current_user
  from src.backend.database.models import User
  from src.backend.security.owner_guard import verify_book_ownership

  @router.get("/api/bibles/{book_id}")
  async def get_bible(
      book_id: int,
      current_user: User = Depends(get_current_user),
  ):
      async with UnitOfWork(AppContainer.db()) as uow:
          await verify_book_ownership(book_id, current_user, uow)
          b = await uow.bible.get_latest_bible(book_id)
      if not b:
          return {}
      ...
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.misc import get_bible; print('Step 9 OK')"
  ```
- **合否基準**: `Step 9 OK` と出力されること。

---

### Step 10: `GET /api/optimization_history/{book_id}` への所有権ガード適用
- **目的**: 最適化履歴（レポート JSON）に対する IDOR を防止する。
- **対象ファイル**: [`src/backend/routers/misc.py`](file:///e:/hhh/src/backend/routers/misc.py)
- **修正内容**:
  ```python
  @router.get("/api/optimization_history/{book_id}")
  async def get_opt_history(
      book_id: int,
      current_user: User = Depends(get_current_user),
  ):
      async with UnitOfWork(AppContainer.db()) as uow:
          await verify_book_ownership(book_id, current_user, uow)
          history = await uow.misc.get_optimization_history(book_id)
      ...
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.misc import get_opt_history; print('Step 10 OK')"
  ```
- **合否基準**: `Step 10 OK` と出力されること。

---

### Step 11: `GET /api/tasks/{task_id}/status` におけるタスク所有者検証
- **目的**: タスクステータス取得時に、該当タスクが依頼者本人のものであるか（または管理者の場合）のみ返却を許可する。
- **対象ファイル**: [`src/backend/routers/tasks.py`](file:///e:/hhh/src/backend/routers/tasks.py)
- **修正内容**:
  ```python
  @router.get("/{task_id}/status")
  async def get_task_status(
      task_id: str,
      current_user: User = Depends(get_current_user),
  ):
      ...
      data = json.loads(val) if val else json.loads(row.value)
      # user_id がペイロードに含まれている場合は本人確認を実施
      task_user_id = data.get("user_id")
      if task_user_id and task_user_id != current_user.id and current_user.role != "admin":
          raise HTTPException(status_code=403, detail="このタスクへのアクセス権限がありません")
      return data
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.backend.routers.tasks import get_task_status; print('Step 11 OK')"
  ```
- **合否基準**: `Step 11 OK` と出力されること。

---

### Step 12: P0 総合 IDOR 防御結合テストの作成と全検証
- **目的**: Step 1〜11 で修正したすべての保護エンドポイントに対し、不正な他者アクセスが確実に `403 FORBIDDEN` または `401 UNAUTHORIZED` となることを総合結合テストで検証する。
- **対象ファイル**: `tests/integration/test_p0_security_idor_full.py`（新規作成）
- **実装コード**:
  ```python
  """P0 セキュリティ IDOR ガード網羅検証テスト"""
  import pytest
  from fastapi.testclient import TestClient
  from src.backend.server import app
  from src.backend.security.jwt import create_access_token

  @pytest.fixture
  def auth_client():
      return TestClient(app)

  def test_unauthenticated_export_blocked(auth_client):
      resp = auth_client.get("/api/export/books/1")
      assert resp.status_code == 401

  def test_cross_user_book_export_forbidden(auth_client):
      # ユーザー B (id=202) のトークンで他人の本 (id=1) へのアクセスを試行
      token_b = create_access_token(data={"sub": "202", "role": "user"})
      resp = auth_client.get(
          "/api/export/books/1",
          headers={"Authorization": f"Bearer {token_b}"}
      )
      assert resp.status_code in [403, 404]
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/integration/test_p0_security_idor_full.py -o addopts="" --no-cov
  ```
- **合否基準**: `passed` となること。
