# PROPOSAL_02 認可ガード・IDOR防止 実装計画書 - 残りタスク詳細

## 完了済みステップ (Steps 1-11)

| Step | 対象 | 状態 |
|------|------|------|
| 1 | `src/backend/security/roles.py` - RBACガード実装 | ✅ 完了 |
| 2 | `src/backend/security/owner_guard.py` - 所有権ガード実装 | ✅ 完了 |
| 3 | `src/backend/routers/anti_ai.py` - Adminガード適用 | ✅ 完了 |
| 4 | `src/backend/routers/cost.py` - Admin/Pro制限適用 | ✅ 完了 |
| 5 | `src/backend/routers/trace.py` - 認証ガード適用 + インポート修正 | ✅ 完了 |
| 6 | `src/backend/routers/plots.py` - 所有権ガード適用 + インポート修正 | ✅ 完了 |
| 7 | `src/backend/routers/branches.py` - 所有権ガード適用 + 全エンドポイント更新 | ✅ 完了 |
| 8 | `src/backend/routers/episodes.py` - 所有権ガード適用 + インポート修正 | ✅ 完了 |
| 9 | `src/backend/routers/multimedia.py` - 所有権ガード適用 + 全エンドポイント更新 | ✅ 完了 |
| 10 | `src/backend/routers/patches.py` - 部分的に完了 (要追加修正) | 🔄 作業中 |
| 11 | `tests/unit/test_security_rbac_owner.py` - 単体テスト | ✅ 完了 (5/5 PASS) |

---

## 残りタスク詳細

### Step 10 完了のための `patches.py` 残り修正

#### 1. `revise_review` 関数に所有権チェック追加 (Line 330-363)

**現状**: `current_user` は受け取っているが `verify_book_ownership` が呼ばれていない

**修正内容**:
```python
@router.post("/patches/reviews/{review_id}/revise", dependencies=[Depends(get_current_user)])
async def revise_review(
    review_id: int, req: ReviseReviewRequest, current_user: User = Depends(get_current_user)
):
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        review = await uow.misc.get_patch_review(review_id)
        if not review:
            raise NotFoundError(
                "Review not found", resource_type="PatchReview", resource_id=str(review_id)
            )

        # ★追加: 所有権確認
        await verify_book_ownership(review["book_id"], current_user, uow)

        if review.get("status") not in ("under_review", "rejected"):
            raise ValidationError(f"Cannot revise review in status: {review.get('status')}")
        # ... 以下既存コード
```

---

#### 2. `get_setting_versions` 関数に認証・所有権チェック追加 (Line 371-380)

**現状**: 認証なし、所有権チェックなし

**修正内容**:
```python
@router.get("/patches/{book_id}/setting-versions", dependencies=[Depends(get_current_user)])
async def get_setting_versions(book_id: int, current_user: User = Depends(get_current_user)):
    """設定バージョン履歴を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # ★追加: 所有権確認
        await verify_book_ownership(book_id, current_user, uow)
        versions = await uow.misc.get_setting_versions(book_id)
    return versions
```

---

#### 3. `get_setting_version` 関数に認証・所有権チェック追加 (Line 383-398)

**現状**: 認証なし、所有権チェックなし

**修正内容**:
```python
@router.get("/patches/{book_id}/setting-versions/{version_number}", dependencies=[Depends(get_current_user)])
async def get_setting_version(book_id: int, version_number: int, current_user: User = Depends(get_current_user)):
    """特定バージョンの設定を取得"""
    from src.backend.database.uow import UnitOfWork

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        # ★追加: 所有権確認
        await verify_book_ownership(book_id, current_user, uow)
        version = await uow.misc.get_setting_version(book_id, version_number)
    if not version:
        raise NotFoundError(
            "Setting version not found",
            resource_type="SettingVersion",
            resource_id=str(version_number),
        )
    return version
```

---

#### 4. `patch_paragraph` 関数の完全書き換え (Line 406-435)

**現状**: `require_api_key` 使用、`episode_id` から `book_id` 取得していない、所有権チェックなし

**修正内容**:
```python
@router.post("/episodes/{episode_id}/patch-paragraph", dependencies=[Depends(get_current_user)])
async def patch_paragraph(
    episode_id: int, req: ParagraphPatchRequest, current_user: User = Depends(get_current_user)
):
    """手動で特定段落のリライトを指示し、即時差分を取得"""
    from src.backend.database.uow import UnitOfWork
    from src.backend.database.models import Chapter

    # Validate paragraph index
    if req.paragraph_index < 0:
        raise HTTPException(status_code=400, detail="Paragraph index must be non-negative")

    async with UnitOfWork(AppContainer.db()) as uow:
        if uow.session is None:
            raise RuntimeError("Database session not initialized")
        
        # episode_id から chapter を取得し book_id を特定
        from sqlalchemy import select
        result = await uow.session.execute(
            select(Chapter).where(Chapter.id == episode_id)
        )
        chapter = result.scalar_one_or_none()
        if not chapter:
            raise NotFoundError("Episode not found", resource_type="Chapter", resource_id=str(episode_id))
        
        book_id = chapter.book_id
        
        # ★所有権確認
        await verify_book_ownership(book_id, current_user, uow)

    # TODO: 実際のパッチロジック実装
    # 現状はダミー実装を維持
    dummy_original = f"This is the original content of paragraph {req.paragraph_index} for episode {episode_id}."
    dummy_patched = f"This is the patched content of paragraph {req.paragraph_index} for episode {episode_id} based on directive: {req.directive}"

    return ParagraphPatchResponse(
        index=req.paragraph_index,
        original_paragraph=dummy_original,
        patched_paragraph=dummy_patched,
    )
```

---

### Step 12: 統合テストの実行と修正

#### 現状のテスト: `tests/integration/test_idor_protection.py`

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

    token_a = create_access_token(user_id=user_a.id, role=user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/books/50", headers=headers_a)
        assert res.status_code in (403, 404), f"Unexpected status: {res.status_code}"
```

#### 実行コマンド
```bash
pytest tests/integration/test_idor_protection.py -v --no-cov
```

#### 期待される結果
- **PASS**: ユーザーAがユーザーBの本（ID=50）にアクセスしようとしたとき 403 または 404 が返る
- テストが失敗する場合: `/api/books/{book_id}` エンドポイントがどのルーターにあるか確認し、そこに所有権チェックが適用されているか確認

---

## 実装順序と検証手順

### Phase 1: patches.py の残り修正 (4タスク)

1. `revise_review` に所有権チェック追加 → `python -m py_compile src/backend/routers/patches.py`
2. `get_setting_versions` に認証・所有権追加 → `python -m py_compile src/backend/routers/patches.py`
3. `get_setting_version` に認証・所有権追加 → `python -m py_compile src/backend/routers/patches.py`
4. `patch_paragraph` 完全書き換え → `python -m py_compile src/backend/routers/patches.py`

### Phase 2: 構文チェック全体

```bash
python -m ruff check src/backend/routers/
python -m py_compile src/backend/routers/patches.py
python -m py_compile src/backend/routers/multimedia.py
python -m py_compile src/backend/routers/branches.py
```

### Phase 3: 単体テスト再実行

```bash
pytest tests/unit/test_security_rbac_owner.py -v --no-cov
```

### Phase 4: 統合テスト実行

```bash
pytest tests/integration/test_idor_protection.py -v --no-cov
```

### Phase 5: 必要に応じた追加テストケース追加

統合テストでカバーすべきエンドポイント例:
- `/api/plots/{book_id}` (GET)
- `/api/branches/{book_id}` (GET)
- `/api/episodes/chapters/{book_id}` (GET)
- `/api/multimedia/media-mix` (POST)
- `/api/patches/{book_id}/pending` (GET)
- `/api/books/{book_id}` (GET) - これがどのルーターにあるか確認必要

---

## 検証コマンド一覧

```bash
# 構文チェック
python -m ruff check src/backend/security/
python -m ruff check src/backend/routers/

# インポート確認
python -c "from src.backend.security.roles import require_admin, UserRole; print('Roles OK')"
python -c "from src.backend.security.owner_guard import verify_book_ownership; print('Owner guard OK')"

# 単体テスト
pytest tests/unit/test_security_rbac_owner.py -v --no-cov

# 統合テスト
pytest tests/integration/test_idor_protection.py -v --no-cov

# 全テスト (時間があれば)
pytest tests/ -v --no-cov -x
```

---

## 完了条件 (Definition of Done)

- [ ] `patches.py` の4つの関数すべてに認証・所有権チェックが適用されている
- [ ] `python -m py_compile src/backend/routers/patches.py` がエラーなく通る
- [ ] `pytest tests/unit/test_security_rbac_owner.py -v --no-cov` が 5/5 PASS
- [ ] `pytest tests/integration/test_idor_protection.py -v --no-cov` が PASS
- [ ] すべてのルーターで `require_api_key` / `validate_api_key_or_raise` が `get_current_user` + `verify_book_ownership` に置き換わっている