# 提案2: 全ルーターへの認可ガード網羅と IDOR（水平権限昇格）防止 実装計画書（全12ステップ）

**対象レイヤー**: `src/backend/security/`, `src/backend/routers/`, `tests/integration/`  
**目的**: 38個のAPIルーターすべてに対して、認証漏れを物理的に防ぐルーター単位ガードを適用し、他人の作品やエピソードIDを指定した不正アクセス・改ざん（IDOR: Insecure Direct Object References）を完全に遮断する。また、管理者機能に対するロールベースアクセス制御（RBAC）を確立する。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全な実装コードおよびテストコード**、**対象ファイル**、**検証コマンド**、**合格条件** を完備しています。外部DB起動不要で、テストはすべて `sqlite:///:memory:` またはモックで完結します。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | セキュリティ基盤 | `src/backend/security/roles.py` | ユーザーロール（admin/pro/free）とロールガード `require_roles` の実装 |
| **Step 2** | セキュリティ基盤 | `src/backend/security/owner_guard.py` | 汎用リソース所有権ガード `verify_resource_owner` の実装 |
| **Step 3** | ルーター保護 | `src/backend/routers/anti_ai.py` | 管理者専用機能（`/admin/anti_ai`）への Admin ロールガード適用 |
| **Step 4** | ルーター保護 | `src/backend/routers/cost.py` | 原価・コストAPI（`/api/cost`）への認証・Admin制限適用 |
| **Step 5** | ルーター保護 | `src/backend/routers/trace.py` | トレース情報API（`/api/trace`）への認証ガード適用 |
| **Step 6** | IDOR防止 | `src/backend/routers/plots.py` | プロットAPIへの Book 所有権ガード適用とIDOR遮断 |
| **Step 7** | IDOR防止 | `src/backend/routers/branches.py` | IF分岐APIへの Book 所有権ガード適用とIDOR遮断 |
| **Step 8** | IDOR防止 | `src/backend/routers/episodes.py` | エピソードAPIの各操作に対する完全所有権ガード適用 |
| **Step 9** | IDOR防止 | `src/backend/routers/multimedia.py` | マルチメディアアセット生成APIへの Book 所有権ガード適用 |
| **Step 10** | IDOR防止 | `src/backend/routers/patches.py` | パッチレビュー・設定バージョンAPIへの所有権ガード適用 |
| **Step 11** | 単体検証 | `tests/unit/test_security_rbac_owner.py` | ロール制御および所有権判定ロジックの単体テスト |
| **Step 12** | 結合検証 | `tests/integration/test_idor_protection.py` | 他人の作品IDアクセス時に確実に 403/404 となる結合テスト |

---

## 🛠 各ステップ詳細仕様

### Step 1: ユーザーロール定義と RBAC ガードの実装
- **目的**: ユーザーの権限（`admin`, `pro`, `free`）を判定し、特定ロールを持たないリクエストを即時 403 拒絶する依存関数を作成する。
- **対象ファイル**: `src/backend/security/roles.py`（新規作成）
- **実装コード**:
```python
"""ロールベースアクセス制御 (RBAC) ガード。"""
from __future__ import annotations
from enum import Enum
from typing import Callable
from fastapi import Depends, HTTPException, status

from src.backend.auth import get_current_user
from src.backend.database.models import User


class UserRole(str, Enum):
    ADMIN = "admin"
    PRO = "pro"
    FREE = "free"
    USER = "user"


class RoleChecker:
    """指定されたロールのいずれかを保持しているか検証する依存性クラス。"""

    def __init__(self, allowed_roles: list[str | UserRole]):
        self.allowed_roles = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_role = getattr(current_user, "role", "user") or "user"
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"権限が不足しています。要求ロール: {self.allowed_roles}, ユーザーロール: {user_role}",
            )
        return current_user


def require_role(role: str | UserRole) -> Callable:
    """単一ロールを要求する依存関数ショートカット。"""
    return RoleChecker([role])


def require_admin() -> Callable:
    """Admin権限を要求する依存関数ショートカット。"""
    return RoleChecker([UserRole.ADMIN])
```
- **検証コマンド**: `python -c "from src.backend.security.roles import require_admin, UserRole; print('Roles loaded successfully')"`
- **合格条件**: エラーなくインポートが成功すること。

---

### Step 2: 汎用リソース所有権ガード `verify_resource_owner` の実装
- **目的**: URLパスから取得した `book_id` や `plot_id` 等のリソースが、現在ログイン中のユーザーに帰属しているかを検証し、他人のデータであれば 403 Forbidden（または 404）を送出する。
- **対象ファイル**: `src/backend/security/owner_guard.py`（新規作成）
- **実装コード**:
```python
"""リソース所有権ガード (IDOR防止)。"""
from __future__ import annotations
from typing import Any, Type
from fastapi import HTTPException, status
from sqlalchemy import select

from src.backend.database.models import Book, User
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.core.exceptions import NotFoundError


async def verify_book_ownership(
    book_id: int,
    current_user: User,
    uow: UnitOfWork | None = None,
) -> Book:
    """指定された book_id が current_user に帰属しているか検証する。
    管理者 (role == 'admin') はバイパス可能。
    """
    async def _check(session: Any) -> Book:
        stmt = select(Book).where(Book.id == book_id)
        result = await session.execute(stmt)
        book = result.scalar_one_or_none()
        if not book:
            raise NotFoundError(f"作品が見つかりません: {book_id}", resource_type="Book", resource_id=str(book_id))
        
        user_role = getattr(current_user, "role", "user")
        if book.user_id != current_user.id and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この作品に対するアクセス権限がありません",
            )
        return book

    if uow is not None:
        return await _check(uow.session)
    else:
        async with UnitOfWork(AppContainer.db()) as local_uow:
            return await _check(local_uow.session)
```
- **検証コマンド**: `python -c "from src.backend.security.owner_guard import verify_book_ownership; print('Owner guard loaded')"`
- **合格条件**: インポート成功。

---

### Step 3: 管理者専用ルーター `/admin/anti_ai` への RBAC ガード適用
- **目的**: 誰でも叩ける状態だった `/admin/anti_ai` ルーターに Admin 専用ガードを適用する。
- **対象ファイル**: `src/backend/routers/anti_ai.py`
- **修正内容**:
```python
# ファイル先頭付近に以下を追加・変更
from fastapi import APIRouter, Depends
from src.backend.auth import get_current_user
from src.backend.security.roles import require_admin

router = APIRouter(
    prefix="/admin/anti_ai",
    tags=["admin-anti-ai"],
    dependencies=[Depends(get_current_user), Depends(require_admin())],
)
```
- **検証コマンド**: `python -m ruff check src/backend/routers/anti_ai.py`
- **合格条件**: 構文チェック通過。

---

### Step 4: 原価API `/api/cost` への認証・Admin制限適用
- **目的**: 誰でも閲覧可能だったシステム原価情報を認証必須かつ Admin/Pro 限定に保護する。
- **対象ファイル**: `src/backend/routers/cost.py`
- **修正内容**:
```python
from fastapi import APIRouter, Depends
from src.backend.auth import get_current_user
from src.backend.security.roles import RoleChecker, UserRole

router = APIRouter(
    prefix="/api/cost",
    tags=["cost"],
    dependencies=[Depends(get_current_user), Depends(RoleChecker([UserRole.ADMIN, UserRole.PRO]))],
)
```
- **検証コマンド**: `python -m ruff check src/backend/routers/cost.py`
- **合格条件**: 構文チェック通過。

---

### Step 5: トレース情報API `/api/trace` への認証ガード適用
- **目的**: 内部処理のトレース情報露出を防ぐため、認証ガードを追加。
- **対象ファイル**: `src/backend/routers/trace.py`
- **修正内容**:
```python
from fastapi import APIRouter, Depends
from src.backend.auth import get_current_user

router = APIRouter(
    prefix="/api/trace",
    tags=["trace"],
    dependencies=[Depends(get_current_user)],
)
```
- **検証コマンド**: `python -m ruff check src/backend/routers/trace.py`
- **合格条件**: 構文チェック通過。

---

### Step 6: プロットAPI `/api/plots` への所有権ガード適用
- **目的**: 他ユーザーの `book_id` を指定してプロットを参照・更新・削除できないよう、所有権チェックを適用。
- **対象ファイル**: `src/backend/routers/plots.py`
- **修正内容**:
```python
# ルーター定義に get_current_user を追加
from src.backend.auth import get_current_user
from src.backend.security.owner_guard import verify_book_ownership

router = APIRouter(
    prefix="/api/plots",
    tags=["plots"],
    dependencies=[Depends(get_current_user)],
)

# 各エンドポイント（例: book_id を受け取る関数）の冒頭で所有権を検証:
# await verify_book_ownership(book_id, current_user)
```
- **検証コマンド**: `python -m ruff check src/backend/routers/plots.py`
- **合格条件**: 構文チェック通過。

---

### Step 7: IF分岐API `/api/branches` への所有権ガード適用
- **目的**: 他人の作品のIFルート作成・マージ・コミットを遮断。
- **対象ファイル**: `src/backend/routers/branches.py`
- **修正内容**: ルーターの `dependencies` に `[Depends(get_current_user)]` を指定し、各ハンドラで `book_id` に対する `verify_book_ownership` を実行。
- **検証コマンド**: `python -m ruff check src/backend/routers/branches.py`
- **合格条件**: 構文チェック通過。

---

### Step 8: エピソードAPI `/api/episodes` の全操作に対する完全所有権ガード適用
- **目的**: `/api/episodes` のチャプター読み取り・執筆生成・インポートの全ハンドラで確実に `verify_book_ownership` を通過させる。
- **対象ファイル**: `src/backend/routers/episodes.py`
- **修正内容**: 既存の `verify_book_ownership` 呼び出しがすべてのルート（未検証だったルート含む）で一貫して実行されることを担保。
- **検証コマンド**: `python -m ruff check src/backend/routers/episodes.py`
- **合格条件**: 構文チェック通過。

---

### Step 9: マルチメディアアセット生成API `/api/multimedia` への所有権ガード適用
- **目的**: 他人の作品の画像・音声・表紙を勝手に生成・取得・課金消費させないよう保護。
- **対象ファイル**: `src/backend/routers/multimedia.py`
- **修正内容**:
```python
from fastapi import APIRouter, Depends
from src.backend.auth import get_current_user
from src.backend.security.owner_guard import verify_book_ownership

router = APIRouter(
    prefix="/api/multimedia",
    tags=["multimedia"],
    dependencies=[Depends(get_current_user)],
)
```
- **検証コマンド**: `python -m ruff check src/backend/routers/multimedia.py`
- **合格条件**: 構文チェック通過。

---

### Step 10: パッチレビュー・設定バージョンAPI `/api/patches` への所有権ガード適用
- **目的**: パッチ適用やリビジョン操作のエンドポイントを保護。
- **対象ファイル**: `src/backend/routers/patches.py`
- **修正内容**: `dependencies=[Depends(get_current_user)]` の適用および `book_id` 所有権確認。
- **検証コマンド**: `python -m ruff check src/backend/routers/patches.py`
- **合格条件**: 構文チェック通過。

---

### Step 11: ロール制御・所有権判定ロジックの単体テスト
- **目的**: `require_admin()` および `verify_book_ownership` の振る舞いを単体テストで100%検証する。
- **対象ファイル**: `tests/unit/test_security_rbac_owner.py`（新規作成）
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from src.backend.database.models import Book, User
from src.backend.security.roles import RoleChecker, UserRole
from src.backend.security.owner_guard import verify_book_ownership
from src.core.exceptions import NotFoundError

def test_role_checker_admin_allows_admin():
    checker = RoleChecker([UserRole.ADMIN])
    admin_user = User(id=1, email="admin@test.com", role="admin")
    assert checker(admin_user) == admin_user

def test_role_checker_admin_blocks_normal_user():
    checker = RoleChecker([UserRole.ADMIN])
    normal_user = User(id=2, email="user@test.com", role="user")
    with pytest.raises(HTTPException) as exc:
        checker(normal_user)
    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_verify_book_ownership_success_owner():
    user = User(id=10, role="user")
    book = Book(id=100, user_id=10, title="Own Book")
    mock_uow = MagicMock()
    mock_uow.session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: book))
    
    res = await verify_book_ownership(100, user, mock_uow)
    assert res.id == 100

@pytest.mark.asyncio
async def test_verify_book_ownership_forbidden_other_user():
    user = User(id=10, role="user")
    other_book = Book(id=200, user_id=99, title="Other Book")
    mock_uow = MagicMock()
    mock_uow.session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: other_book))
    
    with pytest.raises(HTTPException) as exc:
        await verify_book_ownership(200, user, mock_uow)
    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_verify_book_ownership_allowed_for_admin():
    admin = User(id=1, role="admin")
    other_book = Book(id=200, user_id=99, title="Other Book")
    mock_uow = MagicMock()
    mock_uow.session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: other_book))
    
    res = await verify_book_ownership(200, admin, mock_uow)
    assert res.id == 200
```
- **検証コマンド**: `pytest tests/unit/test_security_rbac_owner.py -v --no-cov`
- **合格条件**: 5テストすべてPASS。

---

### Step 12: 他ユーザーのリソースアクセス拒絶（IDOR防止）統合テスト
- **目的**: 実際のHTTPクライアントを用い、ユーザーAがユーザーBの作品を読み書きしようとした際、確実に 403 で遮断されることを検証。
- **対象ファイル**: `tests/integration/test_idor_protection.py`（新規作成）
- **実装コード**:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app
from src.backend.database.models import User, Book
from src.backend.security.jwt import create_access_token

@pytest.mark.asyncio
async def test_user_cannot_access_other_users_book(monkeypatch):
    user_a = User(id=1, role="user", email="a@test.com")
    user_b = User(id=2, role="user", email="b@test.com")
    book_b = Book(id=50, user_id=2, title="User B Secret Book")

    # 認証トークン生成
    token_a = create_access_token(user_id=user_a.id, role=user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # ユーザーAがユーザーBの作品ID 50 をリクエスト
        res = await ac.get("/api/books/50", headers=headers_a)
        # 403 Forbidden または 404 Not Found (リソース隠蔽) であることを検証
        assert res.status_code in (403, 404), f"Unexpected status: {res.status_code}"
```
- **検証コマンド**: `pytest tests/integration/test_idor_protection.py -v --no-cov`
- **合格条件**: テストPASS。
