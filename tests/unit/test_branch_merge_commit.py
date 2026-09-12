"""IFルートマージ確定コミットAPI & 競合解決エンジンの単体テスト (Part 5: Step 57, 58, 60)。"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database.models.base_orm import Base
from src.backend.database.models import Book, Chapter, Branch
from src.backend.database.repositories.branch import BranchRepository
from src.backend.schemas.branch import (
    BranchMergeCommitRequest,
    ResolvedChapterPayload,
)
from src.backend.services.branch_merge_service import BranchMergeService


TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_engine():
    engine = create_async_engine(
        TEST_ASYNC_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    async_session_factory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_commit_success(async_session: AsyncSession):
    """Step 58: 正常系マージコミットの単体テスト。"""
    # 1. 書籍データ作成
    book = Book(title="IF分岐テスト本", genre="ファンタジー", concept="テスト")
    async_session.add(book)
    await async_session.commit()
    await async_session.refresh(book)

    # 2. ブランチ2件作成 (Branch 1: Target, Branch 2: Source)
    branch1 = Branch(
        id=1,
        book_id=book.id,
        name="Main Route",
        parent_id=None,
        fork_ep_num=0,
    )
    branch2 = Branch(
        id=2,
        book_id=book.id,
        name="What-If Route",
        parent_id=1,
        fork_ep_num=1,
    )
    async_session.add(branch1)
    async_session.add(branch2)

    # 3. チャプター作成 (Target ブランチの第1話)
    chap1 = Chapter(
        book_id=book.id,
        branch_id=1,
        ep_num=1,
        title="第1話 本編",
        content="本編の初期テキスト",
        score_story=80,
    )
    async_session.add(chap1)
    await async_session.commit()

    # 4. マージコミット実行
    service = BranchMergeService(async_session)
    request = BranchMergeCommitRequest(
        source_branch_id=2,
        target_branch_id=1,
        merge_ep_num=1,
        resolved_chapters=[
            ResolvedChapterPayload(
                chapter_number=1,
                resolved_content="コンフリクト解決後の確定統合テキスト",
                resolution_strategy="manual",
            )
        ],
        commit_message="Merged IF route into Main branch with manual edits",
    )

    response = await service.commit_merge(book_id=book.id, request=request)

    assert response.success is True
    assert response.target_branch_id == 1
    assert response.updated_chapters_count == 1
    assert response.committed_at

    # 5. DB の章本文が解決後テキストに更新されていることを検証
    stmt = select(Chapter).where(Chapter.book_id == book.id, Chapter.branch_id == 1, Chapter.ep_num == 1)
    res = await async_session.execute(stmt)
    updated_chap = res.scalar_one_or_none()
    assert updated_chap is not None
    assert updated_chap.content == "コンフリクト解決後の確定統合テキスト"

    # 6. IF グラフに MERGE ノードが保存されていることを検証
    branch_repo = BranchRepository(async_session)
    target_graph = await branch_repo.load_branch_graph(1)
    assert target_graph is not None
    assert "merge_ep1" in target_graph.get("nodes", {})
    merge_node = target_graph["nodes"]["merge_ep1"]
    assert merge_node["branch_type"] == "merge"
    assert merge_node["source_branch_id"] == 2
    assert merge_node["resolution_strategies"]["1"] == "manual"


@pytest.mark.asyncio
async def test_rollback(async_session: AsyncSession):
    """Step 57: ロールバック機構のテスト（途中で失敗した場合の整合性）。"""
    book = Book(title="ロールバックテスト本", genre="ファンタジー", concept="テスト")
    async_session.add(book)
    await async_session.commit()
    await async_session.refresh(book)

    branch = Branch(
        id=10,
        book_id=book.id,
        name="Target Branch",
    )
    async_session.add(branch)

    chap = Chapter(
        book_id=book.id,
        branch_id=10,
        ep_num=1,
        title="元のタイトル",
        content="元の本文（変更されてはならない）",
        score_story=75,
    )
    async_session.add(chap)
    await async_session.commit()

    service = BranchMergeService(async_session)
    # 不正な source_branch_id (存在しないブランチ) で実行してエラーを誘発
    invalid_request = BranchMergeCommitRequest(
        source_branch_id=9999,  # 存在しない
        target_branch_id=10,
        merge_ep_num=1,
        resolved_chapters=[
            ResolvedChapterPayload(
                chapter_number=1,
                resolved_content="汚染されたテキスト",
                resolution_strategy="source",
            )
        ],
    )

    with pytest.raises(ValueError):
        await service.commit_merge(book_id=book.id, request=invalid_request)

    # 元の章本文が一切変更されていないことを検証 (ロールバック保証)
    stmt = select(Chapter).where(Chapter.book_id == book.id, Chapter.branch_id == 10, Chapter.ep_num == 1)
    res = await async_session.execute(stmt)
    unchanged_chap = res.scalar_one_or_none()
    assert unchanged_chap.content == "元の本文（変更されてはならない）"


@pytest.mark.asyncio
async def test_validation_errors(async_session: AsyncSession):
    """Step 54: 不正な章番号や空テキスト送信のバリデーション強化テスト。"""
    service = BranchMergeService(async_session)

    # 1. resolved_chapters が空
    req_empty = BranchMergeCommitRequest(
        source_branch_id=1,
        target_branch_id=2,
        merge_ep_num=1,
        resolved_chapters=[],
    )
    with pytest.raises(ValueError, match="No resolved chapters provided"):
        await service.commit_merge(book_id=1, request=req_empty)

    # 2. resolved_content が空文字
    req_blank = BranchMergeCommitRequest(
        source_branch_id=1,
        target_branch_id=2,
        merge_ep_num=1,
        resolved_chapters=[
            ResolvedChapterPayload(
                chapter_number=1,
                resolved_content="   ",
                resolution_strategy="manual",
            )
        ],
    )
    with pytest.raises(ValueError, match="cannot be empty"):
        await service.commit_merge(book_id=1, request=req_blank)

    # 3. 自ブランチへのマージ
    req_self = BranchMergeCommitRequest(
        source_branch_id=1,
        target_branch_id=1,
        merge_ep_num=1,
        resolved_chapters=[
            ResolvedChapterPayload(
                chapter_number=1,
                resolved_content="テキスト",
                resolution_strategy="manual",
            )
        ],
    )
    with pytest.raises(ValueError, match="Cannot merge a branch into itself"):
        await service.commit_merge(book_id=1, request=req_self)
