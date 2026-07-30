"""
tests/integration/test_collab.py

機能6（共同執筆・レビューコメント）の統合テスト。
メンバー管理とコメントのライフサイクルを検証する。
"""
import pytest

from config.container import Container
from src.backend.database.uow import UnitOfWork


@pytest.fixture
def patched_container(real_uow):
    manager = real_uow.db
    original = Container.db
    Container.db = lambda: manager
    yield real_uow
    Container.db = original


@pytest.mark.asyncio
async def test_collab_member_and_comment_lifecycle(real_uow):
    """メンバー追加→コメント投稿→解決→削除 の一連を確認。"""
    async with real_uow as uow:
        book_id = await uow.books.create_book("T", "G", "C", "S", 10, {}, {})

        mid = await uow.collab.add_member(book_id, "編集者A", "editor")
        assert mid > 0
        members = await uow.collab.list_members(book_id)
        assert len(members) == 1
        assert members[0].role == "editor"

        cid = await uow.collab.add_comment(
            book_id=book_id, chapter_ep=1, author_name="編集者A",
            content="ここは説明過多です", anchor_text="～だった。",
        )
        assert cid > 0
        comments = await uow.collab.list_comments(book_id, chapter_ep=1)
        assert len(comments) == 1
        assert comments[0].resolved is False

        n = await uow.collab.resolve_comment(cid, True)
        assert n == 1
        comments2 = await uow.collab.list_comments(book_id, chapter_ep=1)
        assert comments2[0].resolved is True

        n2 = await uow.collab.delete_comment(cid)
        assert n2 == 1
        assert await uow.collab.list_comments(book_id) == []

        n3 = await uow.collab.remove_member(mid)
        assert n3 == 1


@pytest.mark.asyncio
async def test_collab_router_endpoints(patched_container):
    """routers/collab のエンドポイントが実際のDBで動作する。"""
    from src.backend.routers import collab as collab_router
    from src.backend.routers.collab import CommentRequest, MemberRequest

    async with patched_container as uow:
        book_id = await uow.books.create_book("T", "G", "C", "S", 10, {}, {})

    res = await collab_router.add_member(book_id, MemberRequest(user_name="B", role="viewer"))
    assert res["status"] == "success"
    members = await collab_router.list_members(book_id)
    assert len(members) == 1

    cres = await collab_router.add_comment(
        book_id, 2, CommentRequest(author_name="B", content="推敲依頼")
    )
    assert cres["status"] == "success"
    comments = await collab_router.list_comments(book_id, chapter_ep=2)
    assert len(comments) == 1

    rres = await collab_router.resolve_comment(comments[0]["id"], {"resolved": True})
    assert rres["resolved"] is True
